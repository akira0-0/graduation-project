# Task Plan: Workflow Generation API Design

## Task Summary
设计并实现基于 FastAPI 的 RESTful 接口，用于将用户的自然语言意图转换为可执行的工作流 JSON。参考业界成熟平台（如 Coze）的接口设计规范，提供清晰的请求/响应结构。

## Implementation Steps

### TODO: API Infrastructure Setup
- [ ] Add FastAPI and Uvicorn to requirements
- [ ] Create `workflow_engine/api` directory structure
- [ ] Initialize `workflow_engine/api/server.py` with basic health check

### TODO: API Model Definition
- [ ] Define Pydantic models for `GenerateRequest` (intent, model_config)
- [ ] Define Pydantic models for `GenerateResponse` (workflow_json, metadata)
- [ ] Define Error models

### TODO: Core Endpoint Implementation
- [ ] Implement `POST /api/v1/workflows/generate` endpoint
- [ ] Integrate `LLMPlanner` into the endpoint handler
- [ ] Add error handling for generation failures

### TODO: Validation & Testing
- [ ] Create a test script `test_api.py` to verify the endpoint
- [ ] Verify JSON output format matches frontend expectations

## Documentation Requirements
- Add docstrings to API endpoints (Swagger/OpenAPI auto-docs)
- Update README.md with API usage examples