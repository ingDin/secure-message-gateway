Feature: Secure Gateway Integration
  Full pipeline tests for GatewayAsync:
  - schema validation
  - key rotation
  - key loading
  - HMAC verification
  - freshness update
  - audit logging
  - structured response

  Scenario: Full pipeline without rotation
    Given a valid message with correct HMAC
    When the gateway processes the message
    Then the gateway accepts the message
    And the freshness counter is updated
    And the audit log contains exactly 1 entry "MESSAGE_ACCEPTED"

    Scenario: Full rotation pipeline
      Given rotation is required
      And an initial message with a fake key
      When the gateway processes the initial message
      Then the gateway must log an error "HMAC_FAIL"
      When a valid message signed with the rotated key is processed
      Then the gateway accepts the message
      And the freshness counter is updated
      And the audit log contains rotation, HMAC_FAIL and MESSAGE_ACCEPTED

