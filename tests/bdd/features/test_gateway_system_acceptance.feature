Feature: Secure Gateway Acceptance Validation
  Deterministic end-to-end validation of the secure-message-gateway pipeline.

  Background:
    Given a clean gateway environment

  Scenario: Accept valid message
    Given a valid message
    When the gateway processes the message
    Then the gateway responds with "ok"
    And the audit log contains exactly 1 entry "MESSAGE_ACCEPTED"

  Scenario: Reject message with invalid schema
    Given a message missing required fields
    When the gateway processes the message
    Then the gateway responds with "SCHEMA_FAIL"
    And the audit log contains exactly 1 entry "SCHEMA_FAIL"

  Scenario: Reject message with invalid HMAC
    Given a message with an invalid HMAC
    When the gateway processes the message
    Then the gateway responds with "HMAC_FAIL"
    And the audit log contains exactly 1 entry "HMAC_FAIL"

  Scenario: Reject replayed message
    Given a previously accepted message
    And a replayed message with the same counter
    When the gateway processes the message
    Then the gateway responds with "FRESHNESS_FAIL"
    And the audit log contains entries in order:
      | event            |
      | MESSAGE_ACCEPTED |
      | FRESHNESS_FAIL   |

  Scenario: Trigger rotation when interval expired
    Given rotation is required
    And an initial message signed with an outdated key
    When the gateway processes the initial message
    Then the gateway responds with "HMAC_FAIL"
    And the audit log contains "ROTATION" as the first event
    When a valid message signed with the rotated key is processed
    Then the gateway responds with "ok"
    And the audit log contains entries in order:
      | event            |
      | ROTATION         |
      | HMAC_FAIL        |
      | MESSAGE_ACCEPTED |
