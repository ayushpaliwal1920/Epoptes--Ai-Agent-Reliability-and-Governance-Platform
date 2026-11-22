class AgentGuardError(Exception):
    pass


class AuthenticationError(AgentGuardError):
    pass


class APIError(AgentGuardError):
    pass