import { doesNotReject } from "assert"
import { AnyPrincipal } from "aws-cdk-lib/aws-iam"
import { env } from 'process'

describe('call-make-recording', () => {
    beforeEach(() => {
        jest.resetModules()
    })

    let test_event = require("../../events/inbound.json")

    const generic_response = {
        SchemaVersion: '1.0',
        Actions: [],
    }
    const hangup_response = {
        SchemaVersion:"1.0",
        Actions:[
            { Type: "Hangup",
              Parameters:{
                  SipResponseCode:"0",
                  ParticipantTag:""
    }}]}

    function expect_response(event:any, resp:any, done:any) {
        let lam = require("../index")

        lam.handler(event, null, (_: any, r: any) => {
            try {
                expect(r).toEqual(resp)
                done()
            } catch (e) {
                console.log("UNMATCHING RESPONSE: ", r, " TO ", event);
                done(e)
            }
        })
    }

test('empty event', done => {
    let event = {}
    expect_response(event, generic_response, done)
})

test('new inbound call', done => {
    const new_call_result = {
        "SchemaVersion":"1.0",
        "Actions":[
            {"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},
            {"Type":"Speak","Parameters":
                {"Engine":"neural",
                "LanguageCode":"en-US",
                "Text":"<speak>Hello!  Please record a message after the tone, and press pound when you are done.</speak>",
                "TextType":"ssml",
                "VoiceId":"Matthew"}} ],
        "TransactionAttributes":{"state":"new"}}
    expect_response(test_event, new_call_result, done)
})

test('success new', done => {
    console.log("TEST: success new")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "new"}

    const success_new_response = {
        "SchemaVersion":"1.0",
        "Actions":[
            {"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},
            {"Type":"PlayAudio","Parameters":{
                "Repeat":"1",
                "AudioSource":{"Type":"S3","Key":"500hz-beep.wav"}}}],
        "TransactionAttributes":{"state":"beeping"}}
    expect_response(event, success_new_response, done)
})

test('succcess beeping without bucket', done => {
    console.log("TEST: success beeping")

    let bucket_was_set = (env.WAVFILE_BUCKET !== undefined)
    let old_bucket = ''
    if  (bucket_was_set) {
        old_bucket = env.WAVFILE_BUCKET as string
        delete env.WAVFILE_BUCKET
    }

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "beeping"}

    let lam = require("../index")
    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect(r).toEqual(expect.objectContaining({'SchemaVersion':'1.0'}))

            let ra = r.Actions.filter((a:any) => a.Type === 'RecordAudio')
            expect(ra.len == 1)
            expect(ra[0]).toHaveProperty('Parameters.DurationInSeconds')
            expect(ra[0]).toHaveProperty('Parameters.SilenceDurationInSeconds')
            expect(ra[0]).toHaveProperty('Parameters.SilenceThreshold')
            expect(ra[0]).toHaveProperty('Parameters.RecordingDestination')
            expect(ra[0]).toHaveProperty('Parameters.RecordingDestination.BucketName')
            expect(ra[0]).toHaveProperty('Parameters.RecordingDestination.Prefix')
            expect(ra[0].Parameters.RecordingDestination.Type === 'S3')
            expect(ra[0]).toHaveProperty('Parameters.RecordingTerminators')

            expect(r).toEqual(
                expect.objectContaining({'TransactionAttributes': {'state': 'recording'}}) )
            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } finally {
            if (bucket_was_set) {
                env.WAVFILE_BUCKET = old_bucket }
        }
    })
})

test('succcess beeping with bucket', done => {
    console.log("TEST: success beeping")

    let bucket_was_set = (env.WAVFILE_BUCKET !== undefined)
    let old_bucket = ''
    if  (bucket_was_set) {
        old_bucket = env.WAVFILE_BUCKET as string
    }
    env.WAVFILE_BUCKET = 'test_bucket'

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "beeping"}

    let lam = require("../index")
    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect(r).toEqual(expect.objectContaining({'SchemaVersion':'1.0'}))

            let ra = r.Actions.filter((a:any) => a.Type === 'RecordAudio')
            expect(ra.len == 1)
            expect(ra[0]).toHaveProperty('Parameters.DurationInSeconds')
            expect(ra[0]).toHaveProperty('Parameters.SilenceDurationInSeconds')
            expect(ra[0]).toHaveProperty('Parameters.SilenceThreshold')
            expect(ra[0]).toHaveProperty('Parameters.RecordingDestination')
            expect(ra[0].Parameters.RecordingDestination.BucketName == 'test_bucket')
            expect(ra[0]).toHaveProperty('Parameters.RecordingDestination.Prefix')
            expect(ra[0].Parameters.RecordingDestination.Type === 'S3')
            expect(ra[0]).toHaveProperty('Parameters.RecordingTerminators')

            expect(r).toEqual(
                expect.objectContaining({'TransactionAttributes': {'state': 'recording'}}) )
            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } finally {
            if (bucket_was_set) {
                env.WAVFILE_BUCKET = old_bucket 
            } else {
                delete env.WAVFILE_BUCKET
            }
        }
    })
})

test('succcess recording', done => {
    console.log("TEST: success recording")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.ActionData = {  "RecordingDestination":{
        "Type":"S3",
        "BucketName":
        "valid-bucket-name",
        "Prefix":"9ff01357-23c5-4611-9dd3-f05f9d654faa-"
    }}
    event.CallDetails.TransactionAttributes = {"state": "recording"}

    const recording_response = {
        "SchemaVersion":"1.0",
        "Actions":[
            {"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},
            {"Type":"Speak","Parameters":{
                "Engine":"neural",
                "LanguageCode":"en-US",
                "Text":"<speak>Your message said</speak>",
                "TextType":"ssml",
                "VoiceId":"Matthew"}},
            {"Type":"PlayAudio","Parameters":{"Repeat":"1","AudioSource":{"Type":"S3"}}}],
        "TransactionAttributes":{"state":"playing"}}
    
    expect_response(event, recording_response, done)
})

test('succcess playing', done => {
    console.log("TEST: success playing")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.CallDetails.TransactionAttributes = {"state": "playing"}

    let lam = require("../index")

    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(r)

            expect(r).toHaveProperty("Actions")
            expect(r.Actions).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({"Type": "Pause"}),
                    expect.objectContaining({'Type': 'Speak'}),
                    expect.objectContaining({'Type': 'Hangup'})
                ])
            )
            expect(r).toHaveProperty("TransactionAttributes")
            expect(r.TransactionAttributes).toEqual(
                expect.objectContaining({'state':'finishing'})
            )
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
    expect_response(event, generic_response, done)
})

test('second hangup', done => {
    let event = {...test_event}
    event.InvocationEventType = "HANGUP"
    event.CallDetails.Participants[0].Direction = "foobar"
    expect_response(event, generic_response, done)
})

test('new outbound call', done => {
    let event = {...test_event}
    event.InvocationEventType = "NEW_OUTBOUND_CALL"
    expect_response(event, generic_response, done)
})

test('ringing', done => {
    let event = {...test_event}
    event.InvocationEventType = "RINGING"
    expect_response(event, generic_response, done)
})

test('answered', done => {
    let event = {...test_event}
    event.InvocationEventType = "CALL_ANSWERED"
    let answered_response = {
        "SchemaVersion":"1.0",
        "Actions":[
            {"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},
            {"Type":"Speak","Parameters":{"Engine":"neural","LanguageCode":"en-US","Text":"<speak>Hello!  I am just calling you back!  Goodbye!</speak>","TextType":"ssml","VoiceId":"Matthew"}},
            {"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},
            {"Type":"Hangup","Parameters":{"SipResponseCode":"0","ParticipantTag":""}}]}
    expect_response(event, generic_response, done)
})

test('action failed', done => {
    let event = {...test_event}
    event.InvocationEventType = "ACTION_FAILED"
    expect_response(event, generic_response, done)
})

test('bad type', done => {
    let event = {...test_event}
    event.InvocationEventType = "IMBAAD"
    expect_response(event, generic_response, done)
})

})
