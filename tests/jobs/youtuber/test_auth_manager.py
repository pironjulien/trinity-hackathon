import unittest
from unittest.mock import MagicMock, patch, mock_open
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parents[3]))

from jobs.youtuber.auth_manager import GoogleAuthManager

class TestGoogleAuthManager(unittest.TestCase):

    def setUp(self):
        self.manager = GoogleAuthManager()
        # Prevent actual file system operations
        self.manager.secrets_dir = Path("/tmp/mock_secrets")

    @patch("jobs.youtuber.auth_manager.json.load")
    @patch("builtins.open", new_callable=mock_open)
    @patch("google.oauth2.credentials.Credentials.from_authorized_user_info")
    def test_get_credentials_json_hit(self, mock_from_info, mock_file, mock_json_load):
        # Mock credentials
        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds.scopes = ["https://www.googleapis.com/auth/youtube.upload",
                             "https://www.googleapis.com/auth/youtube.readonly",
                             "https://www.googleapis.com/auth/yt-analytics.readonly"]

        mock_from_info.return_value = mock_creds
        mock_json_load.return_value = {"token": "abc"}

        # Mock file existence
        with patch.object(Path, "exists", return_value=True):
            creds = self.manager.get_credentials("en")

        self.assertIsNotNone(creds)
        self.assertTrue(creds.valid)

    @patch("jobs.youtuber.auth_manager.os.getenv")
    def test_get_credentials_env_hit(self, mock_getenv):
        # Mock json miss
        with patch.object(GoogleAuthManager, "_load_from_json", return_value=None):
            # Mock Env
            import base64

            fake_token = {"token": "abc", "refresh_token": "def"}
            fake_token_json = json.dumps(fake_token)
            fake_token_b64 = base64.b64encode(fake_token_json.encode()).decode()

            mock_getenv.return_value = fake_token_b64

            with patch("google.oauth2.credentials.Credentials.from_authorized_user_info") as mock_from_info:
                mock_creds = MagicMock()
                mock_creds.valid = True
                mock_creds.scopes = ["https://www.googleapis.com/auth/youtube.upload",
                                     "https://www.googleapis.com/auth/youtube.readonly",
                                     "https://www.googleapis.com/auth/yt-analytics.readonly"]
                mock_from_info.return_value = mock_creds

                creds = self.manager.get_credentials("en")

                self.assertIsNotNone(creds)
                self.assertTrue(creds.valid)

    @patch("jobs.youtuber.auth_manager.InstalledAppFlow")
    def test_authenticate_interactive(self, mock_flow_class):
        mock_flow = MagicMock()
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        mock_flow_class.from_client_config.return_value = mock_flow

        mock_creds = MagicMock()
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow.credentials = mock_creds

        # Mock client secrets existence
        with patch.object(Path, "exists", return_value=True):
             with patch("jobs.youtuber.auth_manager.GoogleAuthManager._save_to_json"):
                 with patch("builtins.open", mock_open()):
                     success = self.manager.authenticate("en", mode="interactive", force=True)

        self.assertTrue(success)
        mock_flow.run_local_server.assert_called()

    @patch("jobs.youtuber.auth_manager.InstalledAppFlow")
    def test_authenticate_oob_with_callback(self, mock_flow_class):
        mock_flow = MagicMock()
        mock_flow_class.from_client_secrets_file.return_value = mock_flow
        mock_flow_class.from_client_config.return_value = mock_flow

        mock_flow.authorization_url.return_value = ("http://url", "state")

        # Define callback
        callback = MagicMock(return_value="fake_code")

        # Mock client secrets existence
        with patch.object(Path, "exists", return_value=True):
             with patch("jobs.youtuber.auth_manager.GoogleAuthManager._save_to_json"):
                 with patch("builtins.open", mock_open()):
                     success = self.manager.authenticate("en", mode="oob", force=True, interaction_callback=callback)

        self.assertTrue(success)
        callback.assert_called_with("http://url")
        mock_flow.fetch_token.assert_called_with(code="fake_code")

    def test_validate_scopes_failure(self):
        mock_creds = MagicMock()
        mock_creds.scopes = ["https://www.googleapis.com/auth/youtube.upload"] # Missing scopes

        is_valid = self.manager._validate_scopes(mock_creds)
        self.assertFalse(is_valid)

if __name__ == "__main__":
    unittest.main()
