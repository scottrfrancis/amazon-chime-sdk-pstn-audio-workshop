# Amazon Chime SDK PSTN Audio Workshop

## What is the Amazon Chime SDK?

The Amazon Chime SDK is a set of real-time communications components that developers can use to quickly add messaging, audio, video, and screen sharing capabilities to their web or mobile applications.  There are three core parts of the SDK:

* Media Services (real-time audio and video, including SDKs for web and mobile)
* Messaging (server and client-side persistent messaging)
* Public Switched Telephone Network (PSTN) Audio capabilities (phone calls/telephony)

By using the Amazon Chime SDK, developers can help reduce the cost, complexity, and friction of creating and maintaining their own real-time communication infrastructure and services.  In addition, those applications can easily take advantage of advanced voice technologies enabled by machine learning.  [Amazon Voice Focus](https://aws.amazon.com/about-aws/whats-new/2020/08/amazon-chime-introduces-amazon-voice-focus-for-noise-suppression/) for PSTN provides deep learning based noise suppression to reduce unwanted noise on calls.  Use text-to-speech in your application through our native integration to [Amazon Polly](https://aws.amazon.com/polly/) or build real-time phone-call voice chat-bots using native integration with [Amazon Lex](https://aws.amazon.com/lex/).

## What is PSTN Audio?

With PSTN Audio, developers can build custom telephony applications using the agility and operational simplicity of a serverless AWS Lambda function.  Your Lambda functions control the behavior of phone calls, such as playing voice prompts, collecting digits, recording calls, routing calls to the PSTN and Session Initiation Protocol (SIP) devices using Amazon Chime Voice Connector. The following topics provide an overview and architectural information about the PSTN Audio service, including how to build Lambda functions to control calls. You can read our introduction of the service [here](https://docs.aws.amazon.com/chime/latest/dg/build-lambdas-for-sip-sdk.html).

PSTN Audio applications are serverless, deployed as [AWS Lambda functions](https://aws.amazon.com/lambda/).  If you can write relatively simple code in javascript or python then you can build an advanced telephony application.  This workshop aims to teach the basics of how to use the PSTN Audio service and builds successively towards more advanced capability, starting with the absolute basics. 

## What's New in PSTN Audio?

The latest new features that we profile in this workshop are:

* native integration with Amazon Polly (text-to-speech)
* native integration with Amazon Lex (speech-to-text voice bots)
* native integration with Amazon Voice Focus (noise reduction)
* TransactionAttributes to simplify tracking simple call state
## Recommended Background for Developing Amazon Chime SDK PSTN Audio Applications

PSTN Audio applications are serverless application built using [Amazon Lambda](https://aws.amazon.com/lambda/).  Non-trivial applications will need data stores and databases, as well as various other cloud services.  We recommend that developers have at least an introduction to AWS, Lambda, and our automated deploymnet technology.  Free, self-paces online workshops are available for both [Lambda](https://aws.amazon.com/lambda/resources/workshops-and-tutorials/) and [Amazon Cloud Development Kit (CDK)](https://aws.amazon.com/lambda/resources/workshops-and-tutorials/).  Many developers using these technologies leverage Linux environments, and these workshops are built primarily for the Linux/MacOS command line environment (shell).  Familiarity with basic command line operations and tools is expected, but everything in the workshop is spelled out clearly.
## Workshop Preparation

* [Programming Model - READ THIS FIRST](./docs/how-it-works) - how to write software to control PSTN Audio
* [Development Environment](./docs/development-environment) - what you need to install to have a build environment - automation included!
* [Development Tips and Tricks](./docs/tips-and-tricks) - examples and guidance on how to do telephony development - revisit this as you get experience!
* [Deployment Automation](./docs/cdk-overview) - how we provision a PSTN phone number in the cloud and associate it with a lambda
* [Deploy Resources - DO THIS BEFORE THE WORKSHOPS](./docs/FIRST.md) - Do this before you go any farther - this creates your working environment

## Workshop Lessons/Examples

* [Call Recorded Message](./lambdas/call-play-recording) (teaches how to answer a phone call and play a message file)
* [Call Me Back](lambdas/call-me-back) (teaches how to make outbound phone calls using voice-to-text using Amazon Polly)
* [Call and Bridge Another Call](./lambdas/call-and-bridge) (teachs how to bridge calls together, and how to enable/disable Amazon Voice Focus noise suppression)
* [Call a Voice Chat-Bot](./lambdas/call-lex-bot) (teaches how to connect a phone call to an Amazon Lex chat bot)

## Cleanup

Deploying resources from this repository will create CloudFormation stacks.  To remove those running resources you can simply delete the stack.  To do that, you can type "yarn destroy" in the folder where you deployed the resources with "yarn deploy."  

NOTE:  since each of the example lessons in the "lambda" lessons deploys it's own small stack for just that lambda, to completely clean up those resources you should also run "yarn destroy" from each folder where you deploy the lambda.

## Disclaimers

Deploying the Amazon Chime SDK demo applications contained in this repository will cause your AWS Account to be billed for services, including the Amazon Chime SDK, used by the application.  Each of the child workshop lessons also create resources.  To minimize your expenses, after finishing this workshop please delete the resources you created.  This can be done by running 'yarn destroy' from this directory and from each of the workshop lesson folders that you deployed.

The voice prompt audio files are not encrypted, as would be recommended in a production-grade application.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

All code in this repository is licensed under the MIT-0 License. See the LICENSE file.

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0