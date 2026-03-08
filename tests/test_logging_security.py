"""Test that sensitive data is not exposed in debug logging."""

import logging
from io import StringIO

from tests.testmodels import User
from tortoise.contrib.test import TestCase


class TestLoggingSecurity(TestCase):
    """Test cases for ensuring sensitive data is not logged by Tortoise ORM."""

    async def test_query_parameters_not_logged_in_tortoise_db_client(self):
        """Test that query parameters are not logged by tortoise.db_client logger."""
        # Create a string IO to capture log output
        log_capture = StringIO()

        # Get the tortoise db_client logger and add our handler
        logger = logging.getLogger("tortoise.db_client")
        original_level = logger.level
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(name)s:%(levelname)s:%(message)s")
        handler.setFormatter(formatter)

        # Set up logging
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        try:
            # Create a user with potentially sensitive data
            sensitive_email = "admin@secret-company.com"
            sensitive_username = "admin_with_secret_key_123"
            sensitive_bio = "bio with password: my_secret_password_123"

            user = await User.create(
                username=sensitive_username, mail=sensitive_email, bio=sensitive_bio
            )

            # Get the captured log output
            log_output = log_capture.getvalue()

            # Verify that the SQL query structure is still logged
            self.assertIn("INSERT INTO", log_output)
            self.assertIn("user", log_output.lower())

            # Verify that sensitive data is NOT in the log output
            self.assertNotIn(
                sensitive_email, log_output, f"Sensitive email found in log output: {log_output}"
            )
            self.assertNotIn(
                sensitive_username,
                log_output,
                f"Sensitive username found in log output: {log_output}",
            )
            self.assertNotIn(
                sensitive_bio, log_output, f"Sensitive bio found in log output: {log_output}"
            )
            self.assertNotIn(
                "my_secret_password_123",
                log_output,
                f"Sensitive password found in log output: {log_output}",
            )

            # Test UPDATE operation
            log_capture.seek(0)  # Reset the capture
            log_capture.truncate(0)

            new_sensitive_email = "super_secret_admin@classified.gov"
            user.mail = new_sensitive_email
            await user.save()

            log_output = log_capture.getvalue()
            self.assertNotIn(
                new_sensitive_email,
                log_output,
                f"Sensitive email found in UPDATE log: {log_output}",
            )

            # Test SELECT operation
            log_capture.seek(0)  # Reset the capture
            log_capture.truncate(0)

            await User.filter(username=sensitive_username).first()

            log_output = log_capture.getvalue()
            self.assertNotIn(
                sensitive_username,
                log_output,
                f"Sensitive username found in SELECT log: {log_output}",
            )

            # Clean up
            await user.delete()

        finally:
            # Restore original logging setup
            logger.removeHandler(handler)
            logger.setLevel(original_level)
            handler.close()
