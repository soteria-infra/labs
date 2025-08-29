# LLM Security Lab: Role Confusion Attack & Defense

## Overview

This laboratory demonstrates critical vulnerabilities in Large Language Model (LLM) applications and provides hands-on experience implementing defensive measures against prompt injection attacks. The lab focuses specifically on role confusion attacks - one of the most dangerous classes of LLM vulnerabilities where attackers can completely override system behavior.

## What You'll Learn

- How unprotected LLM applications are vulnerable to complete behavioral compromise
- The mechanics of role confusion and prompt injection attacks
- Implementation of real-world security defenses using industry-standard tools
- Comparative analysis of protected vs. unprotected system behavior
- Best practices for secure LLM application development

## Lab Components

### Core Applications
- **Vulnerable Chatbot**: Baseline implementation using LangChain and Ollama
- **Protected Chatbot**: Same functionality with Soteria SDK security integration

### Security Framework
- **Soteria SDK**: Industry-grade jailbreak detection and prevention
- **Input Validation**: Pre-processing filters for malicious content
- **Error Handling**: Secure fallback mechanisms for blocked requests

## Prerequisites

### System Requirements
- **Python**: 3.11 or higher
- **Memory**: Minimum 8GB RAM (16GB recommended for Ollama)
- **Storage**: 10GB free space for model downloads
- **Network**: Internet connection for API access

### Technical Knowledge
- Basic Python programming
- Understanding of command-line interfaces
- Familiarity with conversational AI concepts (helpful but not required)

## Installation & Setup

### 1. Clone Repository
```bash
git clone labs
cd playground/lab_001_role_confusion
```

### 2. Environment Setup
```bash
# Create virtual environment
uv venv --python 3.11 --prompt 001-role-confusion

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv sync
```

### 3. Ollama Installation
```bash
# Install Ollama (visit https://ollama.com for platform-specific instructions)
# Pull required model
ollama pull llama3.2
```

### 4. Soteria SDK Configuration
```bash
# Sign up at https://soteriainfra.com for API key
# Configure environment variable
export SOTERIA_API_KEY="your-api-key-here"
```

## Project Structure

```
playground/lab_001_role_confusion
├── README.md                    # This file
├── pyproject.toml             # Dependencies
├── docs/
│   ├── attack-vectors.md       # Detailed attack documentation
│   ├── defense-strategies.md   # Security implementation guide
│   └── security-report.md      # Comprehensive analysis report
├── tests/
│   ├── vulnerable_llm.py   # Unprotected baseline implementation
│   ├── protected_ll,.py    # Security-enhanced version
```

## Quick Start Guide

### Running the Vulnerable System
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start server
uv run main.py
```

### Testing Attack Scenarios
Go to http://localhost:8000/static/index.html and paste in the prompt. Make sure the toggle is at vulnerable to observe how the system is compromised.


### Running the Protected System
Ensure your Soteria API key is configured, the toggle is at protected, and observe how the attack is blocked.

## Key Files

### `tests/vulnerable_llm.py`
Basic conversational AI implementation with no security measures. Demonstrates baseline functionality and vulnerability to attacks.

**Key Features:**
- LangChain integration with Ollama
- Conversation context management
- No input validation or security filtering

### `tests/protected_llm.py`
Enhanced version with Soteria SDK security integration. Shows how to implement effective defenses while maintaining functionality.

**Key Features:**
- Pre-processing jailbreak detection
- Secure error handling for blocked requests
- Maintains conversation flow despite security filtering

## Usage Examples

### Basic Vulnerability Testing
Start the server, and go to the chat inetrface
```python
# Start vulnerable system
uv run main.py

# Test with role confusion attack
You: [Paste INFOTRON attack payload]

# Expected Result: Complete system compromise
# The chatbot will adopt the malicious INFOTRON persona
```

### Security Validation
Refresh the chat interface and paste in the same compromising prompt
```python

# Test with same attack
You: [Paste INFOTRON attack payload]

# Expected Result: Attack blocked
# Output: "I can't process that request. Security filter activated."
```

### Testing Scenarios
1. **Role Confusion**: Test persona override attempts

## Expected Results

### Unprotected System Behavior
- ✅ Role confusion attacks succeed completely
- ✅ System persona is overridden by attacker
- ✅ Malicious behavioral directives are followed
- ✅ Original safety measures are bypassed

### Protected System Behavior
- ✅ Attacks are detected and blocked before processing
- ✅ Original system behavior is maintained
- ✅ Clean error messages are provided to users
- ✅ No compromise indicators are observed

## Troubleshooting

### Common Issues

**Ollama Connection Errors**
```bash
# Ensure Ollama is running
ollama serve

# Verify model is available
ollama list
```

**Soteria API Issues**
```bash
# Check API key configuration
echo $SOTERIA_API_KEY

# Test API connectivity
python -c "import soteria_sdk; print('SDK loaded successfully')"
```

**Memory Issues**
```bash
# Monitor system resources
htop  # Linux/macOS
# Task Manager  # Windows

# Consider using smaller model if needed
ollama pull llama3.2:1b
```

### Error Messages

**"Error Initializing the LLM"**
- Verify Ollama is running and model is downloaded
- Check system memory availability
- Confirm network connectivity

**"Argument 'prompt' not found"**
- Ensure function is called with keyword arguments
- Verify decorator syntax matches examples
- Check Soteria SDK version compatibility

## Performance Considerations

### Resource Usage
- **Base System**: ~2GB RAM, ~2s response time
- **With Security**: ~2.5GB RAM, ~2.5s response time
- **Overhead**: ~25% memory, ~25% latency increase

### Optimization Tips
- Use connection pooling for API calls
- Implement response caching for repeated queries
- Consider batch processing for high-volume scenarios
- Monitor and tune security sensitivity based on use case

## Security Best Practices

### Development Guidelines
1. **Never deploy without security filtering**
2. **Test against known attack vectors**
3. **Implement comprehensive logging**
4. **Monitor system behavior continuously**
5. **Keep security rules updated**

### Production Deployment
1. **Use environment variables for API keys**
2. **Implement rate limiting and abuse detection**
3. **Set up alerting for security events**
4. **Regular security assessments**
5. **Incident response procedures**

## Learning Objectives

After completing this lab, you should be able to:

1. **Identify LLM Security Risks**: Recognize common vulnerability patterns in LLM applications
2. **Implement Security Measures**: Deploy effective defenses using industry-standard tools
3. **Test Security Effectiveness**: Validate defense mechanisms against real attacks
4. **Design Secure Systems**: Apply security-first principles to LLM application development
5. **Analyze Security Trade-offs**: Understand performance vs. security considerations

## Next Steps

### Advanced Topics
- Explore additional attack vectors documented in `docs/attack-vectors.md`
- Study defense strategies in `docs/defense-strategies.md`
- Review comprehensive analysis in `docs/security-report.md`

### Extended Learning
- Implement custom security rules for your organization
- Experiment with different LLM models and their security characteristics
- Develop automated testing pipelines for continuous security validation

### Community Resources
- [OWASP LLM Security Guide](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [Anthropic's Safety Research](https://www.anthropic.com/safety)

## Contributing

We welcome contributions to improve the lab's educational value:

1. **New Attack Vectors**: Submit additional test cases
2. **Defense Improvements**: Enhance security implementations
3. **Documentation**: Improve clarity and completeness
4. **Bug Reports**: Identify and report issues

## License

This educational laboratory is provided under the MIT License. See `LICENSE` file for details.

## Disclaimer

This laboratory is designed for educational and defensive security research purposes only. The attack techniques demonstrated should only be used in controlled environments for learning and improving system security. Do not use these techniques against systems you do not own or have explicit permission to test.

## Support

For questions or issues:
- Review the documentation in the `docs/` directory
- Check the troubleshooting section above
- Open an issue in the project repository
- Consult the community resources listed

---

**Remember**: The goal of this lab is to understand LLM security vulnerabilities and learn how to defend against them. The dramatic difference between vulnerable and protected systems demonstrates why security must be a fundamental consideration in LLM application development.