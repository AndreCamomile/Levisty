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
        console.log('🚀 NEW: Import playlist request for URL:', url);

        if (!url) {
            console.error('❌ No URL provided in request');
            return res.status(400).json({ error: 'URL is required' });
        }

        console.log('🔍 Validating YouTube URL...');
        if (!isValidYouTubeUrl(url)) {
            console.error('❌ Invalid YouTube URL provided:', url);
            return res.status(400).json({ error: 'Invalid YouTube URL' });
        }

        console.log('🎵 Starting playlist import with new system...');
        
        // Use the new unified Python script
        const pythonProcess = spawn('python3', ['youtube_playlist.py', url]);
        let result = '';
        let errorOutput = '';

        pythonProcess.stdout.on('data', (data) => {
            result += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            errorOutput += data.toString();
            // Log progress messages in real-time
            const lines = data.toString().split('\n');
            lines.forEach(line => {
                if (line.trim()) {
                    console.log('📝 Import log:', line.trim());
                }
            });
        });

        const formattedPlaylist = await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                pythonProcess.kill();
                reject(new Error('Playlist import timed out after 60 seconds'));
            }, 60000); // 60 second timeout

            pythonProcess.on('close', (code) => {
                clearTimeout(timeout);
                
                if (code === 0) {
                    try {
                        const playlist = JSON.parse(result);
                        console.log('✅ Playlist imported successfully:', playlist.name, 'with', playlist.tracks.length, 'tracks');
                        resolve(playlist);
                    } catch (parseError) {
                        console.error('❌ Failed to parse playlist data:', parseError);
                        console.error('Raw output:', result);
                        reject(new Error('Invalid playlist data received'));
                    }
                } else {
                    console.error('❌ Playlist import failed with code:', code);
                    console.error('Error output:', errorOutput);
                    reject(new Error('Playlist import script failed'));
                }
            });

            pythonProcess.on('error', (error) => {
                clearTimeout(timeout);
                console.error('❌ Failed to start playlist import process:', error);
                reject(new Error('Failed to start playlist import: ' + error.message));
            });
        });

        // Validate the result
        if (!formattedPlaylist) {
            return res.status(500).json({ error: 'No playlist data received' });
        }

        if (!formattedPlaylist.tracks || !Array.isArray(formattedPlaylist.tracks)) {
            return res.status(500).json({ error: 'Invalid playlist format - no tracks array' });
        }

        if (formattedPlaylist.tracks.length === 0) {
            return res.status(404).json({ error: 'Playlist is empty or no videos could be extracted' });
        }

        console.log('🎉 Successfully imported playlist:', formattedPlaylist.name, 'with', formattedPlaylist.tracks.length, 'tracks');
        res.json(formattedPlaylist);

    } catch (error) {
        console.error('💥 Playlist import error:', error);
        
        let errorMessage = 'Failed to import playlist';
        
        if (error.message.includes('timed out')) {
            errorMessage = 'Playlist import timed out - the playlist might be too large or unavailable';
        } else if (error.message.includes('private')) {
            errorMessage = 'This playlist is private or contains private videos';
        } else if (error.message.includes('not found') || error.message.includes('404')) {
            errorMessage = 'Playlist not found. Make sure it\'s public and the URL is correct';
        } else if (error.message.includes('blocked')) {
            errorMessage = 'This playlist is blocked in your region';
        } else if (error.message.includes('Invalid')) {
            errorMessage = 'Invalid playlist URL format';
        }
        
        res.status(500).json({ 
            error: errorMessage,
            details: process.env.NODE_ENV === 'development' ? error.message : undefined
        });
    }
});

// Test new playlist import system
app.get('/test-playlist', async (req, res) => {
    try {
        console.log('🧪 Testing new playlist import system...');
        
        const testUrl = 'https://www.youtube.com/playlist?list=PL55713C70BA91BD6E';
        const pythonProcess = spawn('python3', ['youtube_playlist.py', testUrl]);
        let result = '';
        let errorOutput = '';

        pythonProcess.stdout.on('data', (data) => {
            result += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });

        await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                pythonProcess.kill();
                reject(new Error('Test timed out'));
            }, 30000);

            pythonProcess.on('close', (code) => {
                clearTimeout(timeout);
                
                if (code === 0) {
                    try {
                        const testPlaylist = JSON.parse(result);
                        console.log('✅ Test successful:', testPlaylist.name, 'with', testPlaylist.tracks.length, 'tracks');
                        res.json({
                            success: true,
                            playlist: {
                                name: testPlaylist.name,
                                trackCount: testPlaylist.tracks.length,
                                author: testPlaylist.author,
                                sampleTracks: testPlaylist.tracks.slice(0, 3).map(t => t.title)
                            },
                            logs: errorOutput
                        });
                        resolve();
                    } catch (parseError) {
                        console.error('❌ Test failed - parse error:', parseError);
                        res.status(500).json({
                            success: false,
                            error: 'Failed to parse test playlist',
                            rawOutput: result,
                            logs: errorOutput
                        });
                        resolve();
                    }
                } else {
                    console.error('❌ Test failed with code:', code);
                    res.status(500).json({
                        success: false,
                        error: 'Test playlist import failed',
                        exitCode: code,
                        logs: errorOutput
                    });
                    resolve();
                }
            });

            pythonProcess.on('error', (error) => {
                clearTimeout(timeout);
                console.error('❌ Failed to start test:', error);
                res.status(500).json({
                    success: false,
                    error: 'Failed to start test script',
                    details: error.message
                });
                resolve();
            });
        });
    } catch (error) {
        console.error('💥 Test error:', error);
        res.status(500).json({
            success: false,
            error: error.message
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