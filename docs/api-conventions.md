# xBike MRP API Conventions & Standards

All REST API endpoints in the xBike MRP System adhere to uniform naming, response envelopment, error handling, and authentication protocols.

---

## 1. Base URL & Versioning

- Base URL: `/api/v1`
- Swagger Interactive Documentation: `/docs`
- ReDoc Documentation: `/redoc`
- OpenAPI Specification: `/api/v1/openapi.json`

---

## 2. Standard Response Envelopes

### Success Envelope (Single Entity)
```json
{
  "success": true,
  "data": {
    "id": "part_01J8K3M9000",
    "part_number": "XB-FRM-ALU-01",
    "name": "Alloy 6061 Commuter Frame",
    "category": "FRAME",
    "unit": "PCS",
    "created_at": "2026-10-01T12:00:00Z"
  },
  "message": "Resource retrieved successfully"
}
```

### Success Envelope (Paginated Collection)
```json
{
  "success": true,
  "data": [
    { "id": "part_01", "name": "Handlebar Grip" },
    { "id": "part_02", "name": "Bicycle Chain 11-speed" }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 142,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  },
  "message": "Items retrieved successfully"
}
```

---

## 3. Error Envelope & HTTP Status Codes

Standard HTTP status codes are utilized:
- `200 OK`: Request succeeded.
- `201 Created`: Resource was created.
- `204 No Content`: Resource was deleted or action completed without return body.
- `400 Bad Request`: Validation failure or semantic domain invariant broken.
- `401 Unauthorized`: Missing, expired, or invalid JWT authentication token.
- `403 Forbidden`: Authenticated user lacks RBAC permission.
- `404 Not Found`: Target entity does not exist.
- `409 Conflict`: Unique constraint violation (e.g. duplicate part number or serial).
- `422 Unprocessable Entity`: Schema validation error by Pydantic.
- `500 Internal Server Error`: Unhandled server exception.

### Standard Error Body:
```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Cannot issue 15 units of XB-CHN-11S. Only 6 units available in Bin A-12.",
    "details": {
      "part_id": "part_02",
      "requested_quantity": 15,
      "available_quantity": 6
    }
  },
  "timestamp": "2026-10-01T12:05:00Z"
}
```

---

## 4. Query Parameters for Collections

- `page`: 1-based page index (default: `1`).
- `page_size`: Number of records per page (default: `20`, max: `100`).
- `search`: Keyword string for text fields (e.g., SKU, name, supplier).
- `sort_by`: Field name to order results (e.g., `created_at`).
- `sort_order`: `asc` or `desc` (default: `desc`).

---

## 5. Authentication Header

Protected endpoints require the standard Bearer authorization header:
```http
Authorization: Bearer <jwt-token>
```
