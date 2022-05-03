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

import { doesNotReject } from "assert";

describe('call-play-recording', () => {
    beforeEach(() => {
        jest.resetModules()
    })

    let test_event = require("../../events/inbound.json")

    function expect_schema_10(r: any) {
        expect(r).toEqual(expect.objectContaining({'SchemaVersion':'1.0'}))
    }

    function expect_pause(r: any) {
        let rp = r.Actions.filter((a:any) => a.Type === 'Pause')
        expect(rp.len == 1)
        expect(rp[0]).toHaveProperty('Parameters.DurationInMilliseconds')
    }

    function expect_play(r: any) {
        let rp = r.Actions.filter((a:any) => a.Type === 'PlayAudio')
        expect(rp.len == 1)
        expect(rp[0]).toHaveProperty('Parameters.AudioSource')
    }

    function expect_hangup(r: any) {
        let rp = r.Actions.filter((a:any) => a.Type === 'Hangup')
        expect(rp.len == 1)
        expect(rp[0].Parameters.SipResponseCode == 0)
    }

    function call_and_expect(event: any, expectations: any, done: any) {
        require("../index").handler(event, null, (_:any, r:any) => {
            let error = null
            try {
                expectations.forEach((e:any) => {
                    e(r)
                })
            } catch (err: any) {
                error = err
            } finally {
                done(error)
            }
        })
    }

test('empty event', done => {
    let event = {};
    call_and_expect(event, [expect_schema_10], done)
})

test('new call', done => {
    let event = {...test_event}

    call_and_expect(event, [
        expect_schema_10,
        expect_pause,
        expect_play,
        expect_hangup
    ], done)
})

test('sucess', done => {
    let event = {...test_event}
    event.InvocationEventType = "ACTION_SUCCESSFUL"
    call_and_expect(event, [expect_schema_10], done)
})

test('hangup', done => {
    let event = {...test_event}
    event.InvocationEventType = "HANGUP"
    call_and_expect(event, [expect_schema_10], done)
})

test('bad type', done => {
    let event = {...test_event}
    event.InvocationEventType = "IMBAAD"
    call_and_expect(event, [expect_schema_10], done)
})

})
