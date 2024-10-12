def validate_initialise_params(accountId, password, server, path):
    if not accountId:
        return {"status": "failed", "message": "Missing accountId"}
    if not password:
        return {"status": "failed", "message": "Missing password"}
    if not server:
        return {"status": "failed", "message": "Missing server"}
    if not path:
        return {"status": "failed", "message": "Missing path"}
    return None
