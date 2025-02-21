// src/server.ts
import express, {Request, Response, NextFunction} from 'express';
import axios from 'axios';
import sharp from 'sharp';
import dotenv from 'dotenv';
import {URLSearchParams} from 'url';
import * as bmp from 'bmp-js';


dotenv.config();

interface TokenData {
    access_token: string;
    refresh_token: string;
    expires_at: number;
    art?: Buffer;
}

interface TrackResponse {
    track: string;
    artist: string;
    art_url: string;
}

interface SpotifyTokenResponse {
    access_token: string;
    refresh_token: string;
    expires_in: number;
}

interface SpotifyTrackResponse {
    item: {
        name: string;
        artists: Array<{ name: string }>;
        album: {
            images: Array<{ url: string }>;
        };
    };
}

const app = express();
const port = process.env.PORT || 3000;
const tokenStore = new Map<string, TokenData>();

const authMiddleware = (req: Request, res: Response, next: NextFunction) => {
    const userId = req.query.userId as string;
    const tokens = tokenStore.get(userId);

    if (!userId || !tokens) {
        res.status(401).json({error: 'Unauthorized'});
        return;
    }

    if (Date.now() > tokens.expires_at) {
        res.status(401).json({error: 'Token expired'});
        return;
    }

    next();
};

app.get('/login', (req: Request, res: Response) => {
    const params = new URLSearchParams({
        client_id: process.env.SPOTIFY_CLIENT_ID!,
        response_type: 'code',
        redirect_uri: process.env.SPOTIFY_REDIRECT_URI!,
        scope: 'user-read-currently-playing',
        state: req.query.userId as string || 'vobot-user'
    });

    res.redirect(`https://accounts.spotify.com/authorize?${params}`);
});

app.get('/callback', async (req: Request, res: Response) => {
    try {
        const {code, state} = req.query;
        const authHeader = Buffer.from(
            `${process.env.SPOTIFY_CLIENT_ID}:${process.env.SPOTIFY_CLIENT_SECRET}`
        ).toString('base64');

        const response = await axios.post<SpotifyTokenResponse>(
            'https://accounts.spotify.com/api/token',
            new URLSearchParams({
                grant_type: 'authorization_code',
                code: code as string,
                redirect_uri: process.env.SPOTIFY_REDIRECT_URI!
            }),
            {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    Authorization: `Basic ${authHeader}`
                }
            }
        );

        tokenStore.set(state as string, {
            access_token: response.data.access_token,
            refresh_token: response.data.refresh_token,
            expires_at: Date.now() + (response.data.expires_in * 1000)
        });

        res.send('Authentication successful! You can close this window.');
    } catch (error) {
        console.error('Auth error:', error);
        res.status(500).send('Authentication failed');
    }
});

app.get('/current-track', authMiddleware, async (req: Request, res: Response<TrackResponse | { error: string }>) => {
    try {
        const userId = req.query.userId as string;
        const tokens = tokenStore.get(userId)!;

        const trackResponse = await axios.get<SpotifyTrackResponse>(
            'https://api.spotify.com/v1/me/player/currently-playing',
            { headers: { Authorization: `Bearer ${tokens.access_token}` } }
        );

        const trackData = trackResponse.data;
        const artUrl = trackData.item.album.images[0].url;

        // Get image data
        const imageResponse = await axios.get(artUrl, { responseType: 'arraybuffer' });

        // Process with sharp
        const { data, info } = await sharp(Buffer.from(imageResponse.data as any))
            .resize(320, 240)
            .raw()
            .toBuffer({ resolveWithObject: true });

        // Convert to BMP
        const bmpData = bmp.encode({
            data: Buffer.from(data),
            width: info.width,
            height: info.height
        });

        tokenStore.set(userId, { ...tokens, art: bmpData.data });

        res.json({
            track: trackData.item.name,
            artist: trackData.item.artists[0].name,
            art_url: `${req.protocol}://${req.get('host')}/art.bmp?userId=${userId}`
        });
    } catch (error) {
        console.error('Track error:', error);
        res.status(500).json({ error: 'Failed to fetch track' });
    }
});

app.get('/art.bmp', authMiddleware, (req: Request, res: Response) => {
    const userId = req.query.userId as string;
    const art = tokenStore.get(userId)?.art;

    if (!art) {
        res.status(404).send('Art not found');
        return;
    }

    res.set('Content-Type', 'image/bmp');
    res.send(art);
});

setInterval(async () => {
    for (const [userId, tokens] of tokenStore) {
        if (Date.now() > tokens.expires_at - 300000) {
            try {
                const authHeader = Buffer.from(
                    `${process.env.SPOTIFY_CLIENT_ID}:${process.env.SPOTIFY_CLIENT_SECRET}`
                ).toString('base64');

                const response = await axios.post<SpotifyTokenResponse>(
                    'https://accounts.spotify.com/api/token',
                    new URLSearchParams({
                        grant_type: 'refresh_token',
                        refresh_token: tokens.refresh_token
                    }),
                    {
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            Authorization: `Basic ${authHeader}`
                        }
                    }
                );

                tokenStore.set(userId, {
                    ...tokens,
                    access_token: response.data.access_token,
                    expires_at: Date.now() + (response.data.expires_in * 1000)
                });
            } catch (error) {
                console.error(`Refresh failed for ${userId}:`, error);
            }
        }
    }
}, 60000);

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});