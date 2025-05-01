import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import argcomplete

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.labdb.cli import get_path_completions


class TestPathCompletion(unittest.TestCase):
    @patch('src.labdb.cli.Database')
    @patch('src.labdb.cli.load_config')
    @patch('src.labdb.cli.get_current_path')
    def test_empty_prefix_completion(self, mock_get_path, mock_load_config, mock_db_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_get_path.return_value = '/test'
        
        # Mock directory listing
        mock_db.list_dir.return_value = [
            {"path_str": "/test/dir1", "type": "directory"},
            {"path_str": "/test/file1", "type": "experiment"}
        ]
        
        # Test empty prefix (should list all items in current directory)
        completions = get_path_completions("", None)
        self.assertEqual(set(completions), {"dir1/", "file1"})
        mock_db.list_dir.assert_called_with('/test')
    
    @patch('src.labdb.cli.Database')
    @patch('src.labdb.cli.load_config')
    @patch('src.labdb.cli.get_current_path')
    def test_prefix_filtering(self, mock_get_path, mock_load_config, mock_db_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_get_path.return_value = '/test'
        
        # Mock directory listing
        mock_db.list_dir.return_value = [
            {"path_str": "/test/dir1", "type": "directory"},
            {"path_str": "/test/dir2", "type": "directory"},
            {"path_str": "/test/file1", "type": "experiment"}
        ]
        
        # Test with prefix that should filter items
        completions = get_path_completions("d", None)
        self.assertEqual(set(completions), {"dir1/", "dir2/"})
        mock_db.list_dir.assert_called_with('/test')
    
    @patch('src.labdb.cli.Database')
    @patch('src.labdb.cli.load_config')
    @patch('src.labdb.cli.get_current_path')
    @patch('src.labdb.cli.resolve_path')
    def test_multilevel_path(self, mock_resolve_path, mock_get_path, mock_load_config, mock_db_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_get_path.return_value = '/test'
        mock_resolve_path.return_value = '/test/dir1'
        
        # Mock directory listing for nested directory
        mock_db.list_dir.return_value = [
            {"path_str": "/test/dir1/subdir", "type": "directory"},
            {"path_str": "/test/dir1/file", "type": "experiment"}
        ]
        
        # Test multilevel path
        completions = get_path_completions("dir1/s", None)
        # The completions should include the base prefix
        self.assertEqual(set(completions), {"dir1/subdir/"})
        mock_db.list_dir.assert_called_with('/test/dir1')
    
    @patch('src.labdb.cli.Database')
    @patch('src.labdb.cli.load_config')
    @patch('src.labdb.cli.get_current_path')
    def test_absolute_path(self, mock_get_path, mock_load_config, mock_db_class):
        # Setup mocks
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db
        mock_get_path.return_value = '/test'
        
        # Mock directory listing for root
        mock_db.list_dir.return_value = [
            {"path_str": "/dir1", "type": "directory"},
            {"path_str": "/file1", "type": "experiment"}
        ]
        
        # Test absolute path
        completions = get_path_completions("/f", None)
        self.assertEqual(set(completions), {"/file1"})
        mock_db.list_dir.assert_called_with('/')
    
    @patch('src.labdb.cli.Database')
    @patch('src.labdb.cli.load_config')
    @patch('src.labdb.cli.get_current_path')
    def test_error_handling(self, mock_get_path, mock_load_config, mock_db_class):
        # Setup mocks to raise an exception
        mock_db_class.side_effect = Exception("Test error")
        
        # Test that errors are handled gracefully
        completions = get_path_completions("test", None)
        self.assertEqual(completions, [])


if __name__ == '__main__':
    unittest.main() 