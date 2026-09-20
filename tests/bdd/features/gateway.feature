Feature: Secure Gateway Validation
  The gateway must validate messages using schema, HMAC integrity,
  freshness monotonicity and audit logging.

  Scenario: Accept valid message
    Given a valid message
    When the gateway processes the message
    Then the gateway accepts the message

  Scenario: Reject message with invalid HMAC
    Given a message with an invalid HMAC
    When the gateway processes the message
    Then the gateway rejects the message with reason "HMAC_FAIL"

  Scenario: Reject replayed message
    Given a previously accepted message
    And a replayed message with the same counter
    When the gateway processes the message
    Then the gateway rejects the message with reason "FRESHNESS_FAIL"

  Scenario: Reject message with invalid schema
    Given a message with missing required fields
    When the gateway processes the message
    Then the gateway rejects the message with reason "SCHEMA_FAIL"
