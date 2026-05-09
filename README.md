# infra-prompt-engine

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)
![Claude](https://img.shields.io/badge/Claude-API-000000?logo=anthropic)
![License](https://img.shields.io/badge/license-MIT-blue)

Natural language → Terraform → GitHub PR. Describe infrastructure in plain English; this engine calls the Claude API to generate valid Terraform HCL and automatically opens a pull request for human review.

## How It Works

```
User prompt → Claude API (claude-sonnet) → HCL files → GitHub branch → PR → GitHub Actions plan
```

## Skills Demonstrated

`Python` · `Claude API` · `Anthropic SDK` · `GitHub API` · `Terraform` · `AI automation`
