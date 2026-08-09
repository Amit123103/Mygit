# MyGit Remote Wire Protocol (v1) Specification

## 1. Overview & Handshake

The MyGit Remote Wire Protocol (v1) governs object synchronization between local CLI clients and remote MyGit servers over HTTP/HTTPS streams.

### Protocol Headers:
- `User-Agent: MyGit-Client/1.0`
- `X-MyGit-Protocol-Version: 1`
- `Authorization: Bearer <token>`

---

## 2. Reference Discovery Protocol (`GET /info/refs`)

**Request:**
```http
GET /api/v1/repos/owner/repo/info/refs HTTP/1.1
Host: mygit.example.com
X-MyGit-Protocol-Version: 1
```

**Response (JSON):**
```json
{
  "protocol": "v1",
  "refs": {
    "refs/heads/main": "c836b784188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398",
    "refs/heads/feature": "bdb69acad959818609e251778950f250d5d55b40977b8d6f3949da19bba81f7f",
    "refs/tags/v1.0.0": "5f91ac31288f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398"
  }
}
```

---

## 3. Object Push Protocol (`POST /objects/push`)

To push new commits, the client determines missing object SHAs between local HEAD and remote reference, packages them, and uploads them atomically.

**Request Payload:**
```json
{
  "ref": "refs/heads/main",
  "target_sha": "c836b784188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398",
  "objects": [
    {
      "sha": "c836b784188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398",
      "type": "commit",
      "data_hex": "7472656520..."
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "ref_updated": "refs/heads/main",
  "new_sha": "c836b784188f2cc1723e67ad184ffa7937be988afc1b89749976dc13b5db6398"
}
```
