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

import { CfnOutput, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { Chime } from './chime-stack';
import { Application } from './application-stack';

export class AmazonChimeSdkPstnAudioWorkshopStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const application = new Application(this, 'Application', {});

    const chime = new Chime(this, 'Chime', {
      phoneState: 'NM',
      smaLambdaEndpointArn: application.smaLambdaEndpointArn,
    });

    new CfnOutput(this, 'phoneNumber', { value: chime.phoneNumber });
    new CfnOutput(this, 'smaId', { value: chime.smaId });
    new CfnOutput(this, 'smaHandlerArn', { value: application.smaLambdaEndpointArn });
    new CfnOutput(this, 'smaHandlerName', { value: application.smaLambdaName });
    new CfnOutput(this, 'logGroup', { value: application.handlerLambdaLogGroupName });
  }
}

