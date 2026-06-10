# county-records MCP server (planned — Sprint 3+)

Thin MCP server giving Claude live, read-only access to property data sources:
- County assessor card lookup (NJ counties we cover; start with Passaic/Bergen/Essex)
- County clerk deed/record search (covers the GIS lag — see vault note)
- FEMA flood zone by address (National Flood Hazard Layer API)

Design intent: one tool per source, address-in / structured-JSON-out, no
write operations, no credentials for public endpoints. Build with the Python
MCP SDK. Each tool's output should match the fields SOP-order-intake step 4 needs.

Status: placeholder. Groom into the backlog when Sprint 3 starts.
