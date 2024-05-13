# Request Info by Mail or Email With AWS Lexbot and Lambda
**This is a Python project that contains the code for a lambda handler for a Lexbot**
The intended use of the lexbot is to be used within an AWS connect call flow.
The initial prompt would be in the call flow and then the Lambda codehooks would
interact back and forth with the caller to determine how they would like to
recieve information, and then react to the request.

Fallback handling is included to reprompt for intent if the initial attempt fails.

The user can use their keypad or say in natural language what they would like
to do. 

Options:
Press 1 to request a brochure by postal mail
press 2 to subscribe to email news letters

**Option 1**
The bot asks a user to say their address - zip code followed by street address - with reprompting.
Addresses are validated using the AWS Location service to mitigate incorrect speech-to-text translation.

The address will then be stored in a table so that it can be used for a mailing list.

**Option 2**
The bot asks a user to say their email address with reprompting.
The email address is then used to subscribe to an SNS topic to which
messages can be published.


The orange box representing the cloudformation stack is included in this repository.

![Cloud Architecture](https://github.com/yrldark/ContactCenter01/assets/167708797/1c2177c8-d4e8-48ee-aaff-dee52fda914c)
