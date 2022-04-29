import { doesNotReject } from "assert";

describe('call-play-recording', () => {
    beforeEach(() => {
        jest.resetModules()
    })

    let test_event = require("../../events/inbound.json")

    const generic_response = {
        SchemaVersion: '1.0',
        Actions: [],
    }

    function expect_response(event:any, resp:any, done:any) {
        let lam = require("../index")

        lam.handler(event, null, (_: any, r: any) => {
            try {
                expect(r).toEqual(resp)
                done()
            } catch (e) {
                console.log("got response of ", r)
                done(e)
            }
        })
    }

test('empty event', done => {
    let event = {};
    expect_response(event, generic_response, done);
})

test('new call', done => {
    const new_call_result = { "SchemaVersion": "1.0", "Actions": [{ "Type": "Pause", "Parameters": { "DurationInMilliseconds": "1000" } }, { "Type": "PlayAudio", "Parameters": { "Repeat": "1", "AudioSource": { "Type": "S3", "Key": "hello-goodbye.wav" } } }, { "Type": "Hangup", "Parameters": { "SipResponseCode": "0", "ParticipantTag": "" } }], "TransactionAttributes": { "key1": "val1*", "key2": "val2*", "key3": "val3*" } }
    expect_response(test_event, new_call_result, done);
})

test('sucess', done => {
    let event = test_event;
    event.InvocationEventType = "ACTION_SUCCESSFUL";
    expect_response(event, generic_response, done);
})

test('hangup', done => {
    let event = test_event;
    event.InvocationEventType = "HANGUP";
    expect_response(event, generic_response, done);
})

})
