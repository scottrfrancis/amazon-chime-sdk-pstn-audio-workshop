import { doesNotReject } from "assert";

describe('call-me-back', () => {
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
                console.log("UNMATCHING response of ", r)
                done(e)
            }
        })
    }

test('empty event', done => {
    let event = {}
    expect_response(event, generic_response, done)
})

test('new inbound call', done => {
    const new_call_result = {"SchemaVersion":"1.0","Actions":[{"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},{"Type":"Speak","Parameters":{"Engine":"neural","LanguageCode":"en-US","Text":"<speak>Hello!  I will call you back!  Goodbye!</speak>","TextType":"ssml","VoiceId":"Matthew"}},{"Type":"Hangup","Parameters":{"SipResponseCode":"0","ParticipantTag":""}}]}
    expect_response(test_event, new_call_result, done)
})

test('success', done => {
    let event = test_event
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    expect_response(event, hangup_response, done)
})

test('hangup', done => {
    let event = test_event
    event.InvocationEventType = "HANGUP"
    expect_response(event, generic_response, done)
})

test('second hangup', done => {
    let event = test_event
    event.InvocationEventType = "HANGUP"
    event.CallDetails.Participants[0].Direction = "foobar"
    expect_response(event, generic_response, done)
})

test('new outbound call', done => {
    let event = test_event
    event.InvocationEventType = "NEW_OUTBOUND_CALL"
    expect_response(event, generic_response, done)
})

test('ringing', done => {
    let event = test_event
    event.InvocationEventType = "RINGING"
    expect_response(event, generic_response, done)
})

test('answered', done => {
    let event = test_event
    event.InvocationEventType = "CALL_ANSWERED"
    let answered_response = {"SchemaVersion":"1.0","Actions":[{"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},{"Type":"Speak","Parameters":{"Engine":"neural","LanguageCode":"en-US","Text":"<speak>Hello!  I am just calling you back!  Goodbye!</speak>","TextType":"ssml","VoiceId":"Matthew"}},{"Type":"Pause","Parameters":{"DurationInMilliseconds":"1000"}},{"Type":"Hangup","Parameters":{"SipResponseCode":"0","ParticipantTag":""}}]}
    expect_response(event, answered_response, done)
})

test('bad type', done => {
    let event = test_event
    event.InvocationEventType = "IMBAAD"
    expect_response(event, generic_response, done)
})

})
