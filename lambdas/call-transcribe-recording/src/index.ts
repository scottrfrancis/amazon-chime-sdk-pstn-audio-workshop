/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */


import 'source-map-support/register';
import { TranscribeClient, StartTranscriptionJobCommand, GetTranscriptionJobCommand, CallAnalyticsJobStatus } from "@aws-sdk/client-transcribe";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { Stream } from 'stream'

const transcribeClient = new TranscribeClient({});
const wavFileBucket = process.env['WAVFILE_BUCKET'];


let generalResponse: smaResponse = {
  SchemaVersion: '1.0',
  Actions: [],
}

exports.handler = async (event: any, context: any, callback: any) => {
  console.log('Lambda is invoked with calldetails:' + JSON.stringify(event));
  let response = generalResponse;

  switch (event.InvocationEventType) {

    case "NEW_INBOUND_CALL":
      response.Actions = newCall(event);
      response.TransactionAttributes = { "state": "new" };
      break;
    case "ACTION_SUCCESSFUL":
      console.log("ACTION_SUCCESSFUL");
      if (event.CallDetails.TransactionAttributes.state == "new") {
        response.TransactionAttributes = { "state": "beeping" };
        response.Actions = beepCall(event);
      }
      if (event.CallDetails.TransactionAttributes.state == "beeping") {
        response.TransactionAttributes = { "state": "recording" };
        response.Actions = recordCall(event);
      }
      if (event.CallDetails.TransactionAttributes.state == "recording") {
        response.TransactionAttributes = { "state": "transcribing", "params": transcribeParams };
        response.Actions = await transcribeRecording(event);
      }
      if (event.CallDetails.TransactionAttributes.state == "transcribing") {
        response.TransactionAttributes = { "state": "playing" };
        response.Actions = await playbackRecording(event);
      }
      if (event.CallDetails.TransactionAttributes.state == "playing") {
        response.TransactionAttributes = { "state": "finishing" };
        response.Actions = endCall(event);
      }
      break;

    case 'ACTION_FAILED':
      console.log('ACTION_FAILED');
      break;

    case 'HANGUP':
      console.log('HANGUP');
      break;

    default:
      console.log('default case');
      console.log(JSON.stringify(event));
  }
  console.log('Sending response:' + JSON.stringify(response));
  callback(null, response);
};


function newCall(event: any) {
  speakAction.Parameters.Text = "<speak>Hello!  Please record a message after the tone, and press pound when you are done.</speak>";
  return [pauseAction, speakAction];
}

function beepCall(event: any) {
  playAudioAction.Parameters.AudioSource.Key = "500hz-beep.wav";
  return [pauseAction, playAudioAction,];
}

function recordCall(event: any) {
  console.log("wavFileBucket: ", wavFileBucket);
  if (wavFileBucket) {
    recordAudioAction.Parameters.RecordingDestination.BucketName = wavFileBucket;
  }
  recordAudioAction.Parameters.CallId = event.CallDetails.Participants[0].CallId;
  recordAudioAction.Parameters.RecordingDestination.Prefix = event.CallDetails.Participants[0].CallId;

  return [recordAudioAction];
}

async function transcribeRecording(event: any) {
  const s3Uri = "s3://" + event.ActionData.RecordingDestination.BucketName + "/" + event.ActionData.RecordingDestination.Key;
  transcribeParams.TranscriptionJobName = event.CallDetails.Participants[0].CallId;
  transcribeParams.Media.MediaFileUri = s3Uri;
  if (wavFileBucket) {
    transcribeParams.OutputBucketName = wavFileBucket;
  }
  transcribeParams.OutputKey = event.CallDetails.Participants[0].CallId + "/" + event.CallDetails.Participants[0].CallId + ".json";
  console.log("transcribing media at: ", s3Uri);
  try {
    const command = new StartTranscriptionJobCommand(transcribeParams);
    console.log("command:", command);
    const data = await transcribeClient.send(command);
    console.log("Success - put", data);
  } catch (err) {
    console.log("Error", err);
  }
  speakAction.Parameters.Text = "<speak>Transcribing recording, please wait.  This may take up to fifteen seconds.</speak>";
  return [speakAction];
}


async function playbackRecording(event: any) {
  const params = event.CallDetails.TransactionAttributes.params;
  console.log("params:", params);
  var loop = true;
  var status;

  speakAction.Parameters.Text = "<speak>Sorry, we encountered an error transcribing your message</speak>"

  while (loop) {
    status = await getTransaction(event);
    switch (status) {
      case null:
        loop = false;
        console.log("Error: no response object for transcription");
        break;
      case CallAnalyticsJobStatus.COMPLETED:
        console.log("COMPLETED");
        loop = false;
        const result = await downloadFromS3(params);
        var jsonResult: TranscribeResult;
        jsonResult = JSON.parse(result as string);
        const transcript = jsonResult.results.transcripts[0].transcript;
        speakAction.Parameters.Text = "<speak>Your message says, " + transcript + " </speak>";
        break;
      case CallAnalyticsJobStatus.FAILED:
        console.log("FAILED");
        loop = false;
        break;
      case CallAnalyticsJobStatus.IN_PROGRESS:
      case CallAnalyticsJobStatus.QUEUED:
        loop = true; // wait for completion
        await new Promise(r => setTimeout(r, 500));
        break;
    }
  }
  return [speakAction];
}

async function getTransaction(event: any) {

  transcribeParams.TranscriptionJobName = event.CallDetails.Participants[0].CallId;

  var data;
  try {
    const command = new GetTranscriptionJobCommand({ TranscriptionJobName: transcribeParams.TranscriptionJobName });
    data = await transcribeClient.send(command);
  } catch (err) {
    console.log("Error", err);
  }
  if (data) {
    return data.TranscriptionJob?.TranscriptionJobStatus;
  }
  return null;
}


interface Transcript {
  transcript: string;
}

interface Alternative {
  confidence: string;
  content: string;
}

interface Item {
  start_time: string;
  end_time: string;
  alternatives: Alternative[];
  type: string;
}

interface Results {
  transcripts: Transcript[];
  items: Item[];
}

interface TranscribeResult {
  jobName: string;
  accountId: string;
  results: Results;
  status: string;
}

async function downloadFromS3(params: any) {
  const client = new S3Client({});
  const command = new GetObjectCommand({ Bucket: params.OutputBucketName, Key: params.OutputKey });
  console.log("bucket:", params.OutputBucketName);
  console.log("key:   ", params.OutputKey);

  const streamToString = (stream: any) => {
    return new Promise((resolve, reject) => {
      const chunks: any = [];
      stream.on("data", (chunk: any) => chunks.push(chunk));
      stream.on("error", reject);
      stream.on("end", () => resolve(Buffer.concat(chunks).toString("utf-8")));
    });
  };
  try {
    const response = await client.send(command);
    const body = await streamToString(response.Body);
    return body;
  } catch (err) {
    console.log("Error", err);
  }
  return "";
}



function endCall(event: any) {
  speakAction.Parameters.Text = "<speak>Thank you!  Goodbye!</speak>";

  return [pauseAction, speakAction, hangupAction];
}

interface smaAction {
  Type: string;
  Parameters: {};
};
interface smaActions extends Array<smaAction> { };

interface smaResponse {
  SchemaVersion: string;
  Actions: smaActions;
  TransactionAttributes?: Object;
}

const response: smaResponse = {
  SchemaVersion: '1.0',
  Actions: [],
};

const transcribeParams = {
  TranscriptionJobName: "not set",
  LanguageCode: "en-US", // For example, 'en-US'
  MediaFormat: "wav", // For example, 'wav'
  Media: {
    MediaFileUri: "not set",
  },
  OutputBucketName: "not set",
  OutputKey: "not set",
};


const speakAction = {
  Type: "Speak",
  Parameters: {
    Engine: "neural", // Required. Either standard or neural
    LanguageCode: "en-US", // Optional
    Text: "", // Required
    TextType: "ssml", // Optional. Defaults to text
    VoiceId: "Matthew" // Required
  }
}

const speakMessageAction = {
  Type: "Speak",
  Parameters: {
    Engine: "neural", // Required. Either standard or neural
    LanguageCode: "en-US", // Optional
    Text: "", // Required
    TextType: "ssml", // Optional. Defaults to text
    VoiceId: "Joanna" // Required
  }
}


const playAudioAction = {
  Type: "PlayAudio",
  Parameters: {
    Repeat: "1",
    AudioSource: {
      Type: "S3",
      BucketName: wavFileBucket,
      Key: "",
    },
  },
};


const recordAudioAction = {
  Type: "RecordAudio",
  Parameters: {
    CallId: "call-id-1",
    DurationInSeconds: "30",
    SilenceDurationInSeconds: 3,
    SilenceThreshold: 100,
    RecordingTerminators: [
      "#"
    ],
    RecordingDestination: {
      Type: "S3",
      BucketName: "valid-bucket-name",
      Prefix: "valid-prefix-name"
    }
  }
}

const pauseAction = {
  Type: "Pause",
  Parameters: {
    DurationInMilliseconds: "1000",
  },
};

const hangupAction = {
  Type: "Hangup",
  Parameters: {
    SipResponseCode: "0",
    ParticipantTag: "",
  },
};
