import { doesNotReject } from "assert"
import { AnyPrincipal } from "aws-cdk-lib/aws-iam"
import { ENOTEMPTY } from "constants"
import { env } from 'process'

describe('call-and-bridge', () => {
    beforeEach(() => {
        jest.resetModules()
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

    function expect_speak_collect_digits_action(r: any) {
        let rs = r.Actions.filter((a:any) => a.Type === 'SpeakAndGetDigits')
        expect(rs.len == 1)
        expect(rs[0].Parameters).toHaveProperty('CallId')
        expect(rs[0].Parameters).toHaveProperty('SpeechParameters.Text')

        expect(rs[0].Parameters).toHaveProperty('FailureSpeechParameters.Text')
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

test('new inbound call', done => {
    let event = test_event

    let lam = require("../index")
    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_pause(r)
            expect_speak_collect_digits_action(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('succcess speak digits', done => {
    console.log("TEST: success no fallback")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.ActionData = {'Type': 'SpeakAndGetDigits'}
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_pause(r)
            expect_call_and_bridge(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('succcess call and bridge', done => {
    console.log("TEST: success no fallback")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.ActionData = {'Type': 'CallAndBridge'}
    // expects 2 participants... clone and munge the first one
    let participant = {...event.CallDetails.Participants[0]}
    participant.Direction = "Outbound"      // api is looking for an in and out
    event.CallDetails.Participants.push(participant)
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_voice_focus_N(r) // there are TWO of these actions
            expect_receive_digits(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('succcess receive digits', done => {
    console.log("TEST: success no fallback")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.ActionData = {'Type': 'ReceiveDigits'}
    
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

test('succcess voice focus', done => {
    console.log("TEST: success no fallback")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.ActionData = {
        'Type': 'VoiceFocus',
        'Parameters': {
            'Enable': true
        }
    }
    
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

test('succcess other selector', done => {
    console.log("TEST: success no fallback")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.ActionData = {'Type': 'foobar'}
    
    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect(r.Actions.len == 0)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('digits received - 0', done => {
    let event = {...test_event}
    event.InvocationEventType = "DIGITS_RECEIVED"
    event.ActionData = {'Type': 'ReceivedDigits', 'ReceivedDigits': '0'}

    // expects 2 participants... clone and munge the first one
    let participant = {...event.CallDetails.Participants[0]}
    participant.Direction = "Outbound"      // api is looking for an in and out
    event.CallDetails.Participants.push(participant)

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_voice_focus_N(r) // there are TWO of these actions
            expect_receive_digits(r)

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('digits received - 1', done => {
    let event = {...test_event}
    event.InvocationEventType = "DIGITS_RECEIVED"
    event.ActionData = {'Type': 'ReceivedDigits', 'ReceivedDigits': '1'}

    // expects 2 participants... clone and munge the first one
    let participant = {...event.CallDetails.Participants[0]}
    participant.Direction = "Outbound"      // api is looking for an in and out
    event.CallDetails.Participants.push(participant)

    require("../index").handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect_schema_10(r)
            expect_voice_focus_N(r) // there are TWO of these actions
            expect_receive_digits(r)

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
