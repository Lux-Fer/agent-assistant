```mermaid
flowchart LR
  A[用户问题] --> B[调用模型]
  B -->|tool_calls| C[执行工具]
  C --> D[Observation 回填]
  D --> B
  B -->|final answer| E[返回答案]
```
