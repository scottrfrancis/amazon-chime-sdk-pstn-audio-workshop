import { doesNotReject } from "assert"

// spies -- aka Pass-thru-Mocks
import * as Chime from "@aws-sdk/client-chime"
import { resolve } from "dns"
import { send } from "process"
let constructor_call_cnt = 0
let send_force_error = false
const forced_error_message = "forced error"

const consoleSpy = jest.spyOn(console, 'log').mockImplementation()

let original_send:any = null
function my_send<InputType extends object,
    OutputType extends object>(
        command: object, //AWS.Command<AWS.ClientInput, InputType, AWS.ClientOutput, OutputType, AWS.SmithyResolvedConfiguration<AWS.HandlerOptions>>, 
        options?: object //AWS.HandlerOptions
        ): Promise<any> {

    if (!send_force_error && (original_send !== null)) {
        return original_send(command, options)
    } else {
        let p = new Promise((resolve, reject) => {
            reject(forced_error_message)
        })

        return p
    }
}

jest.mock('@aws-sdk/client-chime', () => {
    const original = jest.requireActual('@aws-sdk/client-chime')

    return {
        ...original,
        ChimeClient: jest.fn()
            .mockImplementation((arg) => {
                console.log(arg)
                constructor_call_cnt += 1

                let a_client = new original.ChimeClient(arg)
                if (send_force_error) {
                    original_send = a_client.send
                    a_client.send = my_send
                }

                return a_client
        })
    }
})



describe('call-me-back', () => {
    beforeEach(() => {
        jest.resetModules()
        constructor_call_cnt = 0
        send_force_error = false
        consoleSpy.mockClear()
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

    async function expect_response(event:any, resp:any, done:any) {
        let lam = require("../index")

        await lam.handler(event, null, async (_: any, r: any) => {
            try {
                expect(constructor_call_cnt > 0)
                expect(r).toEqual(resp)
                if (send_force_error) {
                    // need to wait for console log to catch up
                    await new Promise(resolve => setTimeout(resolve, 500));
                    expect(console.log).toHaveBeenCalledWith(forced_error_message)
                }
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

test('first hangup', done => {
    let event = test_event
    event.InvocationEventType = "HANGUP"

    send_force_error = false
    expect_response(event, generic_response, done)
})

test('force hangup error', done => {
    let event = test_event
    event.InvocationEventType = "HANGUP"

    send_force_error = true

    expect_response(event, generic_response, done)
    send_force_error = false    // probably superfluous, beforeEach should reset
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
