"""
Pytest tests for MediaUtils.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from magicplay.utils.media import MediaUtils


class TestMediaUtils:
    """Test MediaUtils functionality."""

    def test_download_video_success(self, tmp_path):
        """Test successful video download."""
        test_url = "http://example.com/test_video.mp4"
        save_path = tmp_path / "test_video.mp4"
        
        # Mock response with content
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-length": "1024"}
        
        # Create mock chunks
        chunk_data = b"fake_video_data" * 100
        mock_response.iter_content = Mock(return_value=[chunk_data[:512], chunk_data[512:]])
        
        with patch('magicplay.utils.media.requests.get') as mock_get:
            mock_get.return_value = mock_response
            
            MediaUtils.download_video(test_url, save_path)
            
            # Verify download was called
            mock_get.assert_called_once_with(test_url, stream=True, timeout=30)
            
            # Verify file was created
            assert save_path.exists()
            assert save_path.stat().st_size > 0
            
            # Verify directory was created
            assert save_path.parent.exists()

    def test_download_video_creates_directory(self, tmp_path):
        """Test that download creates output directory if it doesn't exist."""
        test_url = "http://example.com/test.mp4"
        nested_path = tmp_path / "nested" / "deep" / "test.mp4"
        
        # Directory shouldn't exist yet
        assert not nested_path.parent.exists()
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {"content-length": "512"}
        mock_response.iter_content = Mock(return_value=[b"data"])
        
        with patch('magicplay.utils.media.requests.get') as mock_get:
            mock_get.return_value = mock_response
            
            MediaUtils.download_video(test_url, nested_path)
            
            # Directory should have been created
            assert nested_path.parent.exists()

    def test_download_video_no_content_length(self, tmp_path):
        """Test download when content-length header is missing."""
        test_url = "http://example.com/test.mp4"
        save_path = tmp_path / "test.mp4"
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.headers = {}  # No content-length
        mock_response.content = b"fake_video_data"
        mock_response.iter_content = Mock(return_value=[])
        
        with patch('magicplay.utils.media.requests.get') as mock_get:
            mock_get.return_value = mock_response
            
            MediaUtils.download_video(test_url, save_path)
            
            # Should still work without content-length
            assert save_path.exists()

    def test_download_video_network_error(self, tmp_path):
        """Test download when network request fails."""
        test_url = "http://example.com/test.mp4"
        save_path = tmp_path / "test.mp4"
        
        with patch('magicplay.utils.media.requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            # Should raise exception
            with pytest.raises(Exception, match="Network error"):
                MediaUtils.download_video(test_url, save_path)

    def test_download_video_http_error(self, tmp_path):
        """Test download when HTTP response indicates error."""
        test_url = "http://example.com/test.mp4"
        save_path = tmp_path / "test.mp4"
        
        mock_response = Mock()
        mock_response.raise_for_status = Mock(side_effect=Exception("HTTP 404"))
        mock_response.headers = {"content-length": "0"}
        mock_response.iter_content = Mock(return_value=[])
        
        with patch('magicplay.utils.media.requests.get') as mock_get:
            mock_get.return_value = mock_response
            
            with pytest.raises(Exception, match="HTTP 404"):
                MediaUtils.download_video(test_url, save_path)

    @pytest.mark.parametrize("moviepy_available", [True, False])
    def test_extract_last_frame_moviepy_availability(self, tmp_path, moviepy_available):
        """Test extract_last_frame with and without moviepy."""
        video_path = tmp_path / "test.mp4"
        output_path = tmp_path / "last_frame.png"
        
        # Create dummy video file
        video_path.write_bytes(b"dummy")
        
        with patch('magicplay.utils.media.MOVIEPY_AVAILABLE', moviepy_available):
            if moviepy_available:
                with patch('magicplay.utils.media.VideoFileClip') as mock_clip_class:
                    mock_clip = Mock()
                    mock_clip.__enter__ = Mock(return_value=mock_clip)
                    mock_clip.__exit__ = Mock(return_value=None)
                    mock_clip.duration = 10.0
                    mock_clip.save_frame = Mock()
                    mock_clip_class.return_value = mock_clip
                    
                    result = MediaUtils.extract_last_frame(video_path, output_path)
                    
                    # Should succeed
                    assert result is True
                    mock_clip.save_frame.assert_called_once_with(str(output_path), t=9.9)
            else:
                # Without moviepy, should return False
                result = MediaUtils.extract_last_frame(video_path, output_path)
                assert result is False

    def test_extract_last_frame_exception(self, tmp_path):
        """Test extract_last_frame when exception occurs."""
        video_path = tmp_path / "test.mp4"
        output_path = tmp_path / "last_frame.png"
        
        # Create dummy video file
        video_path.write_bytes(b"dummy")
        
        with patch('magicplay.utils.media.MOVIEPY_AVAILABLE', True):
            with patch('magicplay.utils.media.VideoFileClip') as mock_clip_class:
                mock_clip = Mock()
                mock_clip.__enter__ = Mock(return_value=mock_clip)
                mock_clip.__exit__ = Mock(return_value=None)
                mock_clip.duration = 10.0
                mock_clip.save_frame = Mock(side_effect=Exception("Frame extraction failed"))
                mock_clip_class.return_value = mock_clip
                
                result = MediaUtils.extract_last_frame(video_path, output_path)
                
                # Should return False on exception
                assert result is False

    @pytest.mark.parametrize("moviepy_available", [True, False])
    def test_stitch_videos_moviepy_availability(self, tmp_path, moviepy_available):
        """Test stitch_videos with and without moviepy."""
        video_files = [str(tmp_path / "video1.mp4"), str(tmp_path / "video2.mp4")]
        output_path = tmp_path / "output.mp4"
        
        # Create dummy files
        for video_file in video_files:
            Path(video_file).write_bytes(b"dummy")
        
        with patch('magicplay.utils.media.MOVIEPY_AVAILABLE', moviepy_available):
            if moviepy_available:
                with patch('magicplay.utils.media.VideoFileClip') as mock_clip_class, \
                     patch('magicplay.utils.media.concatenate_videoclips') as mock_concatenate:
                    
                    # Setup mock clips
                    mock_clip1 = Mock()
                    mock_clip1.filename = video_files[0]
                    mock_clip1.size = (1280, 720)
                    mock_clip1.fps = 30
                    mock_clip1.close = Mock()
                    
                    mock_clip2 = Mock()
                    mock_clip2.filename = video_files[1]
                    mock_clip2.size = (1280, 720)
                    mock_clip2.fps = 30
                    mock_clip2.close = Mock()
                    
                    mock_clip_class.side_effect = [mock_clip1, mock_clip2]
                    
                    # Setup final clip
                    mock_final_clip = Mock()
                    mock_final_clip.write_videofile = Mock()
                    mock_final_clip.close = Mock()
                    mock_concatenate.return_value = mock_final_clip
                    
                    MediaUtils.stitch_videos(video_files, output_path)
                    
                    # Verify calls
                    assert mock_clip_class.call_count == 2
                    mock_concatenate.assert_called_once()
                    mock_final_clip.write_videofile.assert_called_once()
                    mock_final_clip.close.assert_called_once()
                    
                    # Verify output directory was created
                    assert output_path.parent.exists()
            else:
                # Without moviepy, should just return
                MediaUtils.stitch_videos(video_files, output_path)
                # Should not create output file
                assert not output_path.exists()

    def test_stitch_videos_empty_list(self, tmp_path):
        """Test stitch_videos with empty video list."""
        output_path = tmp_path / "output.mp4"
        
        with patch('magicplay.utils.media.MOVIEPY_AVAILABLE', True):
            # Should not crash with empty list
            MediaUtils.stitch_videos([], output_path)
            
            # Should not create output file
            assert not output_path.exists()

    def test_stitch_videos_exception(self, tmp_path):
        """Test stitch_videos when exception occurs."""
        video_files = [str(tmp_path / "video1.mp4")]
        output_path = tmp_path / "output.mp4"
        
        # Create dummy file
        Path(video_files[0]).write_bytes(b"dummy")
        
        with patch('magicplay.utils.media.MOVIEPY_AVAILABLE', True):
            with patch('magicplay.utils.media.VideoFileClip') as mock_clip_class:
                mock_clip = Mock()
                mock_clip.filename = video_files[0]
                mock_clip.size = (1280, 720)
                mock_clip.fps = 30
                mock_clip.close = Mock()
                mock_clip_class.return_value = mock_clip
                mock_clip_class.side_effect = Exception("Video loading failed")
                
                # Should raise exception
                with pytest.raises(Exception, match="Video loading failed"):
                    MediaUtils.stitch_videos(video_files, output_path)

    def test_stitch_videos_different_resolutions(self, tmp_path):
        """Test stitch_videos with clips of different resolutions."""
        video_files = [str(tmp_path / "video1.mp4"), str(tmp_path / "video2.mp4")]
        output_path = tmp_path / "output.mp4"
        
        # Create dummy files
        for video_file in video_files:
            Path(video_file).write_bytes(b"dummy")
        
        with patch('magicplay.utils.media.MOVIEPY_AVAILABLE', True):
            with patch('magicplay.utils.media.VideoFileClip') as mock_clip_class, \
                 patch('magicplay.utils.media.concatenate_videoclips') as mock_concatenate:
                
                # Setup mock clips with different resolutions
                mock_clip1 = Mock()
                mock_clip1.filename = video_files[0]
                mock_clip1.size = (1920, 1080)
                mock_clip1.fps = 30
                mock_clip1.close = Mock()
                mock_clip1.resize = Mock(return_value=mock_clip1)
                mock_clip1.resized = Mock(return_value=mock_clip1)
                
                mock_clip2 = Mock()
                mock_clip2.filename = video_files[1]
                mock_clip2.size = (1280, 720)
                mock_clip2.fps = 24
                mock_clip2.close = Mock()
                mock_clip2.resize = Mock(return_value=mock_clip2)
                mock_clip2.resized = Mock(return_value=mock_clip2)
                
                mock_clip_class.side_effect = [mock_clip1, mock_clip2]
                
                # Setup final clip
                mock_final_clip = Mock()
                mock_final_clip.write_videofile = Mock()
                mock_final_clip.close = Mock()
                mock_concatenate.return_value = mock_final_clip
                
                MediaUtils.stitch_videos(video_files, output_path)
                
                # Verify clips were loaded
                assert mock_clip_class.call_count == 2
                
                # Verify resizing may have been called (depending on implementation)
                # We don't assert specific resize calls as implementation may vary

    def test_stitch_videos_cleanup_on_error(self, tmp_path):
        """Test that resources are cleaned up even on error."""
        video_files = [str(tmp_path / "video1.mp4")]
        output_path = tmp_path / "output.mp4"
        
        Path(video_files[0]).write_bytes(b"dummy")
        
        with patch('magicplay.utils.media.MOVIEPY_AVAILABLE', True):
            with patch('magicplay.utils.media.VideoFileClip') as mock_clip_class:
                mock_clip = Mock()
                mock_clip.filename = video_files[0]
                mock_clip.size = (1280, 720)
                mock_clip.fps = 30
                mock_clip.close = Mock()
                mock_clip_class.return_value = mock_clip
                
                with patch('magicplay.utils.media.concatenate_videoclips') as mock_concatenate:
                    mock_final_clip = Mock()
                    mock_final_clip.write_videofile = Mock(side_effect=Exception("Write failed"))
                    mock_final_clip.close = Mock()
                    mock_concatenate.return_value = mock_final_clip
                    
                    try:
                        MediaUtils.stitch_videos(video_files, output_path)
                    except Exception:
                        pass
                    
                    # Verify cleanup was called
                    mock_final_clip.close.assert_called_once()
                    mock_clip.close.assert_called_once()

    def test_path_handling_string_path(self):
        """Test that methods accept string paths."""
        test_url = "http://example.com/test.mp4"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test.mp4")
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-length": "512"}
            mock_response.iter_content = Mock(return_value=[b"data"])
            
            with patch('magicplay.utils.media.requests.get') as mock_get:
                mock_get.return_value = mock_response
                
                # Should accept string path
                MediaUtils.download_video(test_url, save_path)
                
                # Verify file was created
                assert os.path.exists(save_path)

    def test_path_handling_path_object(self):
        """Test that methods accept Path objects."""
        test_url = "http://example.com/test.mp4"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "test.mp4"
            
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.headers = {"content-length": "512"}
            mock_response.iter_content = Mock(return_value=[b"data"])
            
            with patch('magicplay.utils.media.requests.get') as mock_get:
                mock_get.return_value = mock_response
                
                # Should accept Path object
                MediaUtils.download_video(test_url, save_path)
                
                # Verify file was created
                assert save_path.exists()