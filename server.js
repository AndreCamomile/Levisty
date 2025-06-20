const express = require('express');
const path = require('path');
const cors = require('cors');
const ytdl = require('ytdl-core');
const ytpl = require('ytpl');
const { spawn } = require('child_process');
const app = express();

// Middleware setup
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors());

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Cache for search results
const searchCache = new Map();
let lastSearchTime = 0;

// Helper function to validate YouTube URL (including YouTube Music)
function isValidYouTubeUrl(url) {
    const pattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)\/.+/;
    return pattern.test(url);
}

app.post('/search', async (req, res) => {
    try {
        const { query } = req.body;
        if (!query) {
            return res.status(400).json({ error: 'Query is required' });
        }

        // Use system Python
        const pythonProcess = spawn('python3', ['search.py', query]);
        let result = '';
        let error = '';

        pythonProcess.stdout.on('data', (data) => {
            result += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            error += data.toString();
            // Log warning messages but don't treat them as errors
            if (error.includes('Unexpected renderer encountered')) {
                console.warn('YouTube API warning:', error);
            } else {
                console.error('Search error:', error);
            }
        });

        pythonProcess.on('close', (code) => {
            try {
                // Even if there are warnings, try to parse the results
                const videos = JSON.parse(result);
                if (videos && Array.isArray(videos) && videos.length > 0) {
                    return res.json(videos);
                }
                // If no results or empty array
                return res.status(404).json({ error: 'No results found' });
            } catch (parseError) {
                console.error('Failed to parse search.py output:', parseError);
                return res.status(500).json({ error: 'Failed to parse search results' });
            }
        });

        // Handle process errors
        pythonProcess.on('error', (error) => {
            console.error('Failed to start Python process:', error);
            res.status(500).json({ error: 'Failed to start search process' });
        });
    } catch (error) {
        console.error('Search error:', error);
        res.status(500).json({ error: 'Search failed' });
    }
});

// Stream endpoint
app.get('/stream/:videoId', (req, res) => {
    const videoId = req.params.videoId;
    console.log('Streaming video:', videoId);

    // Set headers for audio streaming
    res.setHeader('Content-Type', 'audio/mp4');
    res.setHeader('Accept-Ranges', 'bytes');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const pythonProcess = spawn('python3', ['stream.py', videoId]);
    let error = '';

    // Handle errors
    pythonProcess.stderr.on('data', (data) => {
        error += data.toString();
        console.error(`Streaming error: ${data}`);
    });

    // Stream the audio data
    pythonProcess.stdout.pipe(res);

    // Handle process completion
    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error('Stream process exited with code:', code);
            console.error('Error output:', error);
            if (!res.headersSent) {
                res.status(500).json({ error: 'Streaming failed', details: error });
            }
        }
    });

    // Handle client disconnect
    req.on('close', () => {
        pythonProcess.kill();
    });
});

app.post('/import-playlist', async (req, res) => {
    try {
        const { url } = req.body;
        console.log('Import playlist request for URL:', url);

        if (!url) {
            return res.status(400).json({ error: 'URL is required' });
        }

        if (!isValidYouTubeUrl(url)) {
            return res.status(400).json({ error: 'Invalid YouTube URL' });
        }

        // Extract playlist ID from URL
        let playlistId;
        try {
            console.log('Extracting playlist ID from URL...');
            
            // Manual extraction as backup for ytpl.getPlaylistID
            const urlPatterns = [
                /[&?]list=([^&]+)/,           // Standard YouTube playlist
                /playlist\?list=([^&]+)/,     // Direct playlist link
                /music\.youtube\.com\/playlist\?list=([^&]+)/ // YouTube Music playlist
            ];
            
            let match = null;
            for (const pattern of urlPatterns) {
                match = url.match(pattern);
                if (match) break;
            }
            
            if (match) {
                playlistId = match[1];
                console.log('Manually extracted playlist ID:', playlistId);
            } else {
                // Try ytpl method
                playlistId = await ytpl.getPlaylistID(url);
                console.log('YTPL extracted playlist ID:', playlistId);
            }
        } catch (error) {
            console.error('Error extracting playlist ID:', error);
            return res.status(400).json({ error: 'Invalid playlist URL. Make sure the playlist is public and the URL is correct.' });
        }

        // Try multiple methods to get playlist data
        let formattedPlaylist;
        
        try {
            // Method 1: Try ytpl library
            console.log('Fetching playlist data with ytpl...');
            const playlist = await ytpl(playlistId, {
                limit: 50, // Limit to 50 items to avoid timeouts
                requestOptions: {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                }
            });

            console.log('Playlist fetched with ytpl:', playlist?.title, 'Items:', playlist?.items?.length);

            if (playlist && playlist.items && playlist.items.length > 0) {
                formattedPlaylist = {
                    id: playlist.id,
                    name: playlist.title || 'Untitled Playlist',
                    description: playlist.author?.name ? `by ${playlist.author.name}` : 'YouTube Playlist',
                    isYouTube: true,
                    author: playlist.author?.name || 'Unknown',
                    coverImage: playlist?.bestThumbnail?.url || 
                               playlist?.thumbnails?.[0]?.url || 
                               (playlist.items?.[0]?.bestThumbnail?.url) || 
                               (playlist.items?.[0]?.thumbnails?.[0]?.url) || null,
                    tracks: playlist.items.map(item => ({
                        id: item.id,
                        title: item.title || 'Untitled',
                        thumbnail: item?.bestThumbnail?.url || item?.thumbnails?.[0]?.url || null,
                        channel: item?.author?.name || 'Unknown Channel',
                        duration: item.duration || 'Unknown'
                    })).filter(track => track.id) // Filter out items without IDs
                };
            }
        } catch (ytplError) {
            console.warn('ytpl failed, trying Python method:', ytplError.message);
            
            // Method 2: Use Python script as fallback
            try {
                console.log('Fetching playlist data with Python script...');
                const pythonProcess = spawn('python3', ['playlist_import.py', url]);
                let result = '';
                let error = '';

                pythonProcess.stdout.on('data', (data) => {
                    result += data.toString();
                });

                pythonProcess.stderr.on('data', (data) => {
                    error += data.toString();
                    console.log('Python playlist import log:', data.toString());
                });

                await new Promise((resolve, reject) => {
                    pythonProcess.on('close', (code) => {
                        if (code === 0) {
                            try {
                                formattedPlaylist = JSON.parse(result);
                                console.log('Playlist imported with Python:', formattedPlaylist.name, 'with', formattedPlaylist.tracks.length, 'tracks');
                                resolve();
                            } catch (parseError) {
                                console.error('Failed to parse Python output:', parseError);
                                reject(new Error('Failed to parse playlist data'));
                            }
                        } else {
                            console.error('Python script failed with code:', code);
                            console.error('Python error output:', error);
                            reject(new Error('Python playlist import failed'));
                        }
                    });

                    pythonProcess.on('error', (error) => {
                        console.error('Failed to start Python process:', error);
                        reject(new Error('Failed to start Python playlist import'));
                    });
                });
            } catch (pythonError) {
                console.error('Python method also failed:', pythonError.message);
                throw new Error('Both ytpl and Python methods failed to import playlist');
            }
        }

        if (!formattedPlaylist || !formattedPlaylist.tracks || formattedPlaylist.tracks.length === 0) {
            return res.status(404).json({ error: 'Playlist is empty or not found' });
        }

        console.log('Final formatted playlist:', formattedPlaylist.name, 'with', formattedPlaylist.tracks.length, 'tracks');
        res.json(formattedPlaylist);
    } catch (error) {
        console.error('Error importing playlist - Full error:', error);
        console.error('Error stack:', error.stack);
        
        let errorMessage = 'Failed to import playlist';
        
        if (error.message.includes('private')) {
            errorMessage = 'This playlist contains private videos or is private';
        } else if (error.message.includes('not found') || error.message.includes('404')) {
            errorMessage = 'Playlist not found. Make sure it\'s public and the URL is correct';
        } else if (error.message.includes('age')) {
            errorMessage = 'Some videos in this playlist are age-restricted';
        } else if (error.message.includes('blocked')) {
            errorMessage = 'This playlist is blocked in your region';
        } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
            errorMessage = 'Network error: Cannot connect to YouTube';
        }
        
        res.status(500).json({ 
            error: errorMessage,
            details: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).json({ error: 'Internal server error' });
});

// Handle 404
app.use((req, res) => {
    res.status(404).json({ error: 'Not found' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
}); 