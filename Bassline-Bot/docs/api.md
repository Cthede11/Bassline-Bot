# API Documentation

Bassline-Bot provides a comprehensive REST API for integration and management.

## Base URL
```
http://localhost:8080/api/v1
```

## Authentication

### API Keys
```http
Authorization: Bearer your_api_key_here
```

### OAuth2 (Coming Soon)
```http
Authorization: Bearer oauth2_access_token
```

## Core Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "version": "1.0.0",
  "uptime": 3600
}
```

### Bot Statistics
```http
GET /api/v1/stats
```

**Response:**
```json
{
  "total_guilds": 150,
  "total_users": 25000,
  "active_connections": 45,
  "songs_played_today": 1250,
  "total_playlists": 500,
  "avg_response_time": 0.15
}
```

## Guild Management

### Get Guilds
```http
GET /api/v1/guilds
```

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (default: 50, max: 100)
- `search` (string): Search guild names
- `active_only` (boolean): Show only guilds with active connections

**Response:**
```json
{
  "guilds": [
    {
      "id": "123456789",
      "name": "My Discord Server",
      "is_active": true,
      "queue_length": 5,
      "now_playing": {
        "title": "Never Gonna Give You Up",
        "duration": 212,
        "position": 45
      },
      "settings": {
        "max_queue_size": 100,
        "dj_role_id": "987654321",
        "auto_disconnect": 300,
        "prefix": "!bl"
      },
      "last_activity": 1642204800
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "total_pages": 3
  }
}
```

### Get Guild Details
```http
GET /api/v1/guilds/{guild_id}
```

**Response:**
```json
{
  "id": "123456789",
  "name": "My Discord Server",
  "settings": {
    "max_queue_size": 100,
    "dj_role_id": "987654321",
    "auto_disconnect_timeout": 300,
    "bass_boost_enabled": true,
    "prefix": "!bl"
  },
  "current_session": {
    "is_connected": true,
    "queue_length": 5,
    "now_playing": {
      "title": "Never Gonna Give You Up",
      "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
      "duration": 212,
      "position": 45,
      "requested_by": "user_id_here"
    },
    "loop_mode": "off"
  }
}
```

### Update Guild Settings
```http
PUT /api/v1/guilds/{guild_id}/settings
```

**Request Body:**
```json
{
  "max_queue_size": 150,
  "auto_disconnect_timeout": 600,
  "bass_boost_enabled": false,
  "prefix": "!music"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Settings updated successfully",
  "settings": {
    "max_queue_size": 150,
    "auto_disconnect_timeout": 600,
    "bass_boost_enabled": false,
    "prefix": "!music"
  }
}
```

## Music Control

### Get Queue
```http
GET /api/v1/guilds/{guild_id}/queue
```

**Response:**
```json
{
  "guild_id": "123456789",
  "now_playing": {
    "title": "Never Gonna Give You Up",
    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "duration": 212,
    "position": 45,
    "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/default.jpg",
    "requested_by": {
      "id": "user_id",
      "username": "RickRoller"
    },
    "started_at": "2025-01-15T10:30:00Z"
  },
  "queue": [
    {
      "position": 1,
      "title": "Darude - Sandstorm",
      "url": "https://youtube.com/watch?v=y6120QOlsfU",
      "duration": 222,
      "thumbnail": "https://img.youtube.com/vi/y6120QOlsfU/default.jpg",
      "requested_by": {
        "id": "user_id_2",
        "username": "SandstormLover"
      },
      "added_at": "2025-01-15T10:32:00Z"
    }
  ],
  "total_duration": 222
}
```

### Add Song to Queue
```http
POST /api/v1/guilds/{guild_id}/queue
```

**Request Body:**
```json
{
  "query": "Never Gonna Give You Up",
  "user_id": "123456789",
  "position": "end"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Song added to queue",
  "song": {
    "title": "Rick Astley - Never Gonna Give You Up",
    "duration": 212,
    "position_in_queue": 6
  }
}
```

### Control Playback
```http
POST /api/v1/guilds/{guild_id}/playback
```

**Request Body:**
```json
{
  "action": "skip",
  "user_id": "123456789"
}
```

**Actions:** `play`, `pause`, `skip`, `stop`, `shuffle`

**Response:**
```json
{
  "success": true,
  "message": "Playback skipped",
  "now_playing": {
    "title": "Next song title",
    "duration": 180
  }
}
```

## Playlists (In Progress)

### Get Playlists
```http
GET /api/v1/guilds/{guild_id}/playlists
```

**Query Parameters:**
- `owner_id` (string): Filter by playlist owner
- `public_only` (boolean): Show only public playlists

**Response:**
```json
{
  "playlists": [
    {
      "id": 1,
      "name": "Chill Vibes",
      "description": "Relaxing music for studying",
      "owner": {
        "id": "user_id",
        "username": "PlaylistMaster"
      },
      "song_count": 25,
      "total_duration": 5400,
      "is_public": true,
      "play_count": 42,
      "created_at": "2025-01-10T15:30:00Z"
    }
  ]
}
```

### Create Playlist
```http
POST /api/v1/guilds/{guild_id}/playlists
```

**Request Body:**
```json
{
  "name": "My Awesome Playlist",
  "description": "Collection of favorite songs",
  "owner_id": "123456789",
  "is_public": false
}
```

### Add Song to Playlist
```http
POST /api/v1/playlists/{playlist_id}/songs
```

**Request Body:**
```json
{
  "title": "Song Title",
  "url": "https://youtube.com/watch?v=example",
  "duration": 180,
  "added_by": "123456789"
}
```

## Real-time Data

### Get Real-time Bot Status
```http
GET /api/v1/realtime
```

**Response:**
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "bot_status": "online",
  "guilds": 150,
  "users": 25000,
  "voice_connections": [
    {
      "guild_id": "123456789",
      "channel": "Music",
      "is_playing": true,
      "is_paused": false,
      "current_song": "Never Gonna Give You Up",
      "queue_length": 5
    }
  ],
  "active_queues": {
    "123456789": {
      "length": 5,
      "duration": 1200,
      "next_song": "Darude - Sandstorm"
    }
  },
  "total_active_connections": 45,
  "total_queued_songs": 250,
  "loop_states": {
    "123456789": "OFF",
    "987654321": "SINGLE"
  }
}
```

## User Management

### Get User Statistics
```http
GET /api/v1/users/{user_id}/stats
```

**Response:**
```json
{
  "user_id": "123456789",
  "username": "MusicLover",
  "total_songs_played": 1250,
  "total_playtime": 86400,
  "favorite_genres": ["Rock", "Pop", "Electronic"],
  "most_played_song": {
    "title": "Never Gonna Give You Up",
    "play_count": 47
  },
  "preferences": {
    "bass_boost_enabled": true,
    "default_volume": 0.7,
    "auto_join_voice": false
  }
}
```

### Update User Preferences
```http
PUT /api/v1/users/{user_id}/preferences
```

**Request Body:**
```json
{
  "bass_boost_enabled": false,
  "default_volume": 0.5,
  "auto_join_voice": true
}
```

## Analytics

### Get Usage Analytics
```http
GET /api/v1/analytics/usage
```

**Query Parameters:**
- `start_date` (string): Start date (ISO format)
- `end_date` (string): End date (ISO format)
- `guild_id` (string): Filter by specific guild

**Response:**
```json
{
  "period": {
    "start": "2025-01-08T00:00:00Z",
    "end": "2025-01-15T00:00:00Z"
  },
  "total_commands": 15420,
  "successful_commands": 14876,
  "failed_commands": 544,
  "success_rate": 96.47,
  "most_used_commands": [
    {"command": "play", "count": 8234},
    {"command": "queue", "count": 2156},
    {"command": "skip", "count": 1893}
  ],
  "peak_usage_hours": [20, 21, 22],
  "unique_users": 2847,
  "unique_guilds": 156
}
```

### Get Performance Metrics
```http
GET /api/v1/analytics/performance
```

**Response:**
```json
{
  "avg_response_time": 0.156,
  "p95_response_time": 0.450,
  "p99_response_time": 1.200,
  "error_rate": 0.035,
  "uptime_percentage": 99.97,
  "memory_usage": {
    "current": 512.5,
    "peak": 789.2,
    "average": 445.8
  },
  "cpu_usage": {
    "current": 25.4,
    "peak": 78.9,
    "average": 32.1
  }
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_GUILD_ID",
    "message": "The specified guild ID is invalid or not found",
    "details": {
      "guild_id": "invalid_id",
      "suggestion": "Check that the guild ID is correct and the bot is in that server"
    },
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_GUILD_ID` | 404 | Guild not found or bot not in server |
| `PERMISSION_DENIED` | 403 | User lacks required permissions |
| `QUEUE_FULL` | 409 | Queue has reached maximum capacity |
| `NO_VOICE_CONNECTION` | 400 | Bot not connected to voice channel |
| `INVALID_SONG_URL` | 400 | Provided URL is not a valid music source |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests in time window |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **General endpoints**: 100 requests per minute per IP
- **Music control**: 30 requests per minute per guild
- **Playlist management**: 20 requests per minute per user

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1642204800
```

## Webhooks

### Configure Webhook
```http
POST /api/v1/webhooks
```

**Request Body:**
```json
{
  "url": "https://your-server.com/webhook",
  "events": ["song_started", "queue_updated", "bot_joined", "bot_left"],
  "secret": "your_webhook_secret"
}
```

### Webhook Events

#### Song Started
```json
{
  "event": "song_started",
  "timestamp": "2025-01-15T10:30:00Z",
  "guild_id": "123456789",
  "data": {
    "song": {
      "title": "Never Gonna Give You Up",
      "duration": 212,
      "requested_by": "user_id"
    }
  }
}
```

#### Queue Updated
```json
{
  "event": "queue_updated",
  "timestamp": "2025-01-15T10:30:00Z",
  "guild_id": "123456789",
  "data": {
    "action": "added",
    "queue_length": 6,
    "song": {
      "title": "Darude - Sandstorm",
      "position": 6
    }
  }
}
```

## SDK Examples

### Python
```python
import requests

# Initialize client
class BasslineBotAPI:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def get_guild_queue(self, guild_id):
        response = requests.get(
            f"{self.base_url}/api/v1/guilds/{guild_id}/queue",
            headers=self.headers
        )
        return response.json()
    
    def add_song(self, guild_id, query, user_id):
        data = {"query": query, "user_id": user_id}
        response = requests.post(
            f"{self.base_url}/api/v1/guilds/{guild_id}/queue",
            json=data,
            headers=self.headers
        )
        return response.json()

# Usage
api = BasslineBotAPI("http://localhost:8080", "your_api_key")
queue = api.get_guild_queue("123456789")
result = api.add_song("123456789", "Never Gonna Give You Up", "user_id")
```

### JavaScript
```javascript
class BasslineBotAPI {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async getGuildQueue(guildId) {
        const response = await fetch(
            `${this.baseUrl}/api/v1/guilds/${guildId}/queue`,
            { headers: this.headers }
        );
        return await response.json();
    }
    
    async addSong(guildId, query, userId) {
        const response = await fetch(
            `${this.baseUrl}/api/v1/guilds/${guildId}/queue`,
            {
                method: 'POST',
                headers: this.headers,
                body: JSON.stringify({ query, user_id: userId })
            }
        );
        return await response.json();
    }
}

// Usage
const api = new BasslineBotAPI('http://localhost:8080', 'your_api_key');
const queue = await api.getGuildQueue('123456789');
const result = await api.addSong('123456789', 'Never Gonna Give You Up', 'user_id');
```

## Pagination

All list endpoints support pagination:

```http
GET /api/v1/guilds?page=2&limit=25
```

**Response includes pagination metadata:**
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 25,
    "total": 150,
    "total_pages": 6,
    "has_next": true,
    "has_prev": true,
    "next_page": 3,
    "prev_page": 1
  }
}
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
```
GET /api/v1/docs
```

This provides an interactive API explorer with all endpoints, parameters, and response schemas.