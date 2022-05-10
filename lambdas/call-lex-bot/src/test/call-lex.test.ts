import { doesNotReject } from "assert"
import { AnyPrincipal } from "aws-cdk-lib/aws-iam"
import { env } from 'process'

describe('call-lex-bot', () => {
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
    let event = test_event

    let lam = require("../index")
    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect(r).toEqual(expect.objectContaining({'SchemaVersion':'1.0'}))

            let rp = r.Actions.filter((a:any) => a.Type === 'Pause')
            expect(rp.len == 1)
            expect(rp[0]).toHaveProperty('Parameters.DurationInMilliseconds')

            let rv = r.Actions.filter((a:any) => a.Type === 'VoiceFocus')
            expect(rv.len == 1)
            expect(rv[0].Parameters.Enable)
            expect(rv[0].Parameters).toHaveProperty('CallId')
            
            let rs = r.Actions.filter((a:any) => a.Type === 'StartBotConversation')
            expect(rs.len == 1)
            expect(rs[0].Parameters).toEqual(
                expect.objectContaining({
                    'Configuration': {
                        'SessionState': {
                            'DialogAction': {
                                'Type': "ElicitIntent"
                        }},
                        'WelcomeMessages': [{
                            'ContentType': "PlainText",
                            'Content': "Welcome to AWS Chime SDK Voice Service. Please say what you would like to do.  For example: I'd like to book a room, or, I'd like to rent a car."
                        }],
                    },
                    'LocaleId': 'en_US'
                }) 
            )
            expect(rs[0].Parameters).toHaveProperty('BotAliasArn')

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('action succcess without fallback', done => {
    console.log("TEST: success no fallback")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"

    let lam = require("../index")
    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect(r).toEqual(expect.objectContaining({'SchemaVersion':'1.0'}))

            let rp = r.Actions.filter((a:any) => a.Type === 'Pause')
            expect(rp.len == 1)
            expect(rp[0]).toHaveProperty('Parameters.DurationInMilliseconds')

            let rh = r.Actions.filter((a:any) => a.Type == 'Hangup')
            expect(rh.len == 1)
            expect(rh[0].Parameters).toEqual(
                expect.objectContaining({
                    'SipResponseCode': "0",
                    'ParticipantTag': "",
            }) )

            done()
        } catch (e) {
            console.log("UNMATCHING RESPONSE: ", r, " TO ", event)
            done(e)
        } 
    })
})

test('action succcess WITH fallback', done => {
    console.log("TEST: success ON fallback")

    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    event.ActionData = {'IntentResult':{'SessionState':{'Intent':{'Name':"FallbackIntent"}}}}

    let lam = require("../index")
    lam.handler(event, null, (_: any, r: any) => {
        try {
            console.log(JSON.stringify(r))

            expect(r).toEqual(expect.objectContaining({'SchemaVersion':'1.0'}))

            let rp = r.Actions.filter((a:any) => a.Type === 'Pause')
            expect(rp.len == 1)
            expect(rp[0]).toHaveProperty('Parameters.DurationInMilliseconds')

            let rs = r.Actions.filter((a:any) => a.Type === 'StartBotConversation')
            expect(rs.len == 1)
            expect(rs[0].Parameters).toEqual(
                expect.objectContaining({
                    'Configuration': {
                        'SessionState': {
                        'DialogAction': {
                            'Type': "ElicitIntent"
                        }
                        },
                        'WelcomeMessages': [
                        {
                            'ContentType': "PlainText",
                            'Content': "Welcome to AWS Chime SDK Voice Service. Please say what you would like to do.  For example: I'd like to book a room, or, I'd like to rent a car."
                        },
                    ]},
                    'LocaleId': 'en_US'
            }) )
            expect(rs[0].Parameters).toHaveProperty('BotAliasArn')

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

test('bad type', done => {
    let event = {...test_event}
    event.InvocationEventType = "IMBAAD"
    expect_response(event, generic_response, done)
})

})
