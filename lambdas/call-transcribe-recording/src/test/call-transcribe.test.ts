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

import { doesNotReject } from "assert"
import { AnyPrincipal } from "aws-cdk-lib/aws-iam"
import { env } from 'process'
import { PollyClient, SynthesizeSpeechCommand } from "@aws-sdk/client-polly";


let transcribeConstructorCallCount = 0
let startTranscriptionJobCommandCallCnt = 0
let getTranscriptionJobCommandCallCnt = 0
let s3ConstructorCallCount = 0

// set validate manually as the call to polly is long and can muck up the tests
let validateSpeakText = false

let original_send:any = null
let send_force_error = false
let send_force_okay = true
let forced_error_message = 'forced error'
function my_send<InputType extends object,
    OutputType extends object>(
        command: object, //AWS.Command<AWS.ClientInput, InputType, AWS.ClientOutput, OutputType, AWS.SmithyResolvedConfiguration<AWS.HandlerOptions>>, 
        options?: object //AWS.HandlerOptions
        ): Promise<any> {

    if (send_force_error) {
        return new Promise((resolve, reject) => {
            reject(forced_error_message)
        })
    } else if (send_force_okay) {
        return new Promise((resolve) => {
            resolve(0)
        })
    } else {
        expect(original_send !== undefined)
        return original_send(command, options)
    }
    return original_send(command, options)
}

jest.mock('@aws-sdk/client-transcribe', () => {
    const original = jest.requireActual('@aws-sdk/client-transcribe')

    return {
        ...original,
        TranscribeClient: jest.fn()
            .mockImplementation((arg) => {
                transcribeConstructorCallCount += 1

                let a_client = new original.TranscribeClient(arg)
                if (send_force_error || send_force_okay) {
                    original_send = a_client.send
                    a_client.send = my_send
                }

                return a_client
        }),
        StartTranscriptionJobCommand: jest.fn()
            .mockImplementation((arg) => {
                startTranscriptionJobCommandCallCnt += 1

                let command = {
                    "middlewareStack": {},
                    "input": { ...arg }
                }
                return command
        }),
        GetTranscriptionJobCommand: jest.fn()
            .mockImplementation((arg) => {
                getTranscriptionJobCommandCallCnt += 1

                let command = {
                    "middlewareStack": {},
                    "input": { ...arg }
                }
                return command
        })        
    }
})

jest.mock('@aws-sdk/client-s3', () => {
    const original = jest.requireActual('@aws-sdk/client-s3')

    return {
        ...original,
        S3Client: jest.fn()
            .mockImplementation((arg) => {
                console.log(arg)
                s3ConstructorCallCount += 1

                let a_client = new original.S3Client(arg)
                return a_client
        })
    }
})

const region_to_use = process.env['AWS_DEFAULT_REGION'] || 'us-west-2'
const polly = new PollyClient({ region: region_to_use })

const WAVFILE_BUCKET_VAR = 'WAVFILE_BUCKET'
const fakeBucket = 'fake-bucket'
describe('call-transcribe', () => {
    beforeEach(() => {
        jest.resetModules()

        transcribeConstructorCallCount = 0
        s3ConstructorCallCount = 0
        startTranscriptionJobCommandCallCnt = 0
        getTranscriptionJobCommandCallCnt = 0

        process.env[WAVFILE_BUCKET_VAR] = fakeBucket
    })

    let test_event = require("../../events/inbound.json")

    const hangup_response = {
        SchemaVersion:"1.0",
        Actions:[
            { Type: "Hangup",
              Parameters:{
                  SipResponseCode:"0",
                  ParticipantTag:""
    }}]}

    function expect_schema_10(r: any) {
        expect(r).toEqual(expect.objectContaining({'SchemaVersion':'1.0'}))
    }

    function expect_pause(r: any) {
        let rp = r.Actions.filter((a:any) => a.Type === 'Pause')
        expect(rp.len == 1)
        expect(rp[0]).toHaveProperty('Parameters.DurationInMilliseconds')
    }

    function expect_hangup(r: any) {
        let rp = r.Actions.filter((a:any) => a.Type === 'Hangup')
        expect(rp.len == 1)
        expect(rp[0]).toHaveProperty('Parameters.SipResponseCode')
    }

    function expect_play_audio(r: any, bucketName=fakeBucket) {
        let rp = r.Actions.filter((a:any) => a.Type === 'PlayAudio')
        expect(rp.len == 1)

        expect(rp[0]).toHaveProperty('Parameters.AudioSource.Key')
        expect(rp[0]).toHaveProperty('Parameters.AudioSource.Type')
        expect(rp[0].Parameters.AudioSource.BucketName).toEqual(bucketName)
    }

    function expect_record_audio(r: any) {
        let rp = r.Actions.filter((a:any) => a.Type === 'RecordAudio')
        expect(rp.len == 1)

        expect(rp[0]).toHaveProperty('Parameters.CallId')
        expect(rp[0]).toHaveProperty('Parameters.DurationInSeconds')
        expect(rp[0]).toHaveProperty('Parameters.SilenceDurationInSeconds')
        expect(rp[0]).toHaveProperty('Parameters.SilenceThreshold')
        expect(rp[0]).toHaveProperty('Parameters.RecordingTerminators')
        expect(rp[0]).toHaveProperty('Parameters.RecordingDestination.Type')
        if (process.env[WAVFILE_BUCKET_VAR] !== undefined)
            expect(rp[0]).toHaveProperty('Parameters.RecordingDestination.BucketName')
        expect(rp[0]).toHaveProperty('Parameters.RecordingDestination.Prefix')
    }

    async function expect_speak_action(r: any, done: any) {
        let rs = r.Actions.filter((a:any) => a.Type === 'Speak')
        expect(rs.len == 1)
        expect(rs[0].Parameters).toHaveProperty('Engine')
        expect(rs[0].Parameters).toHaveProperty('Text')
        expect(rs[0].Parameters).toHaveProperty('VoiceId')

        // early exit unless this global is set truthy
        if (!validateSpeakText) {
            done()
            return
        }

        // validate the text
        const input = {
            ...rs[0].Parameters,
            OutputFormat: 'mp3'
        }
        const command = new SynthesizeSpeechCommand(input)
        await polly.send(command)
            .then( (resp) => {
                done()
            }, (error) => {
                done(error)
        }) 

        await new Promise(resolve => setTimeout(resolve, 1000))
        }

    function expect_call_and_bridge(r: any) {
        let rc = r.Actions.filter((a:any) => a.Type === 'CallAndBridge')
        expect(rc.len == 1)
        expect(rc[0].Parameters).toHaveProperty('CallerIdNumber')

        rc[0].Parameters.Endpoints.forEach((e: any) => {
            expect(e).toHaveProperty('Uri')
            expect(e).toHaveProperty('BridgeEndpointType')
        })
    }

    function expect_voice_focus_N(r: any) {
        let rv = r.Actions.filter((a:any) => a.Type === 'VoiceFocus')
        // there can be multiples of this action!
        rv.forEach((v: any) => {
            expect(v.Parameters).toHaveProperty('Enable')
            expect(v.Parameters).toHaveProperty('CallId')
        })
    }

    function expect_receive_digits(r: any) {
        let rd = r.Actions.filter((a:any) => a.Type === 'ReceiveDigits')
        expect(rd.len == 1)
        expect(rd[0].Parameters).toHaveProperty('InputDigitsRegex')
    }

    function expect_transaction_attributes(r: any, attrs: any) {
        expect(r.TransactionAttributes).toEqual(expect.objectContaining(attrs))
    }

test('empty event', done => {
    let event = {}
    require("../index").handler(event, null, (_: any, r: any) => {     
        try {
            expect_schema_10(r)
            done()
        } catch (e) {
            console.log("FAILURE: ", e, " from ", r)
            done(e)
        }
    })
})


test('intantiates Transcribe Client', done => {
    expect(transcribeConstructorCallCount).toEqual(0)

    require("../index").handler({}, null, (_: any, r: any) => {
        expect(transcribeConstructorCallCount).toBeGreaterThanOrEqual(1)
        done()
    })
})


test('wavFileBucket from env var', done => {
    expect(process.env[WAVFILE_BUCKET_VAR]).toEqual(fakeBucket)
    process.env[WAVFILE_BUCKET_VAR] = 'a-test-bucket'

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "new"}
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect_play_audio(r, 'a-test-bucket')
            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('new inbound call', done => {
    let event = {...test_event}
    event.InvocationEventType = "NEW_INBOUND_CALL"

    let lam = require("../index")
    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_pause(r)

            expect_transaction_attributes(r, { "state": "new" })

            expect_speak_action(r, done)
            // done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('succcess new', done => {
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "new"}
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_pause(r)
            expect_play_audio(r)

            expect_transaction_attributes(r, { "state": "beeping" })

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

function expect_beeping(done: any) {
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "beeping"}
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_record_audio(r)

            expect_transaction_attributes(r, { "state": "recording" })

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
}

test('succcess beeping', done => {
    expect_beeping(done)
})

test('success beeping no bucket', done => {
    delete process.env[WAVFILE_BUCKET_VAR]
    expect(process.env[WAVFILE_BUCKET_VAR]).toBeUndefined()

    expect_beeping(done)
})

function expect_recording(done: any) {
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "recording"}
    event.ActionData = { "RecordingDestination": {
        "BucketName": "recording-bucket",
        "Key": "recording-key"
    }}
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect(startTranscriptionJobCommandCallCnt).toBeGreaterThanOrEqual(1)
            expect_schema_10(r)

            expect_transaction_attributes(r, { "state": "transcribing" })
            
            expect_speak_action(r, done)
            // done()       // done is delegated to the speak_action
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
}

test('succcess recording send okay', done => {
    send_force_error = false; send_force_okay = true
    expect_recording(done)
})

test('succcess recording send err', done => {
    send_force_error = true; send_force_okay = false
    expect_recording(done)
})

test('succcess recording no wavFileBucket', done => {
    delete process.env[WAVFILE_BUCKET_VAR]

    send_force_error = false; send_force_okay = true
    expect_recording(done)
})

function expect_transcribing(done: any) {
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "transcribing"}
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect(getTranscriptionJobCommandCallCnt).toBeGreaterThanOrEqual(1)

            expect_schema_10(r)
            expect_transaction_attributes(r, { "state": "playing"})
            
            expect_speak_action(r, done)
            // done()           // done is delegated to the speak_action
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
}

test('succcess transcribing okay', done => {
    send_force_error = false; send_force_okay = true;
    expect_transcribing(done)
})

test('succcess transcribing err', done => {
    send_force_error = true; send_force_okay = false;
    expect_transcribing(done)
})

test('success playing', done =>{
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "playing"}

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect_schema_10(r)
            expect_transaction_attributes(r, { "state": "finishing" })
            expect_pause(r)
            expect_hangup(r)

            expect_speak_action(r, done)
            // done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('success finishing', done =>{
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "finishing"}

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect_schema_10(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('success bad state', done =>{
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "bogus"}

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect_schema_10(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('success empty state', done =>{
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {}

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect_schema_10(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('action failed', done => {
    let event = {...test_event}
    event.InvocationEventType = "ACTION_FAILED"

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            expect_schema_10(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('hangup', done => {
    let event = {...test_event}
    event.InvocationEventType = "HANGUP"

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect(r.Actions.length == 0)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('bad type', done => {
    let event = {...test_event}
    event.InvocationEventType = "IMBAAD"

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect(r.Actions.length == 0)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

})
