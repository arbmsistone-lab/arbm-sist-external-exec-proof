from pathlib import PurePosixPath

ALLOWED_SECRET_PREFIX="mission/"

def namespace(mission_id: str) -> str:
    safe="".join(c if c.isalnum() or c in "-_." else "_" for c in mission_id)[:80]
    if not safe:
        raise ValueError("MISSION_ID_INVALID")
    return f"missions/{safe}/"

def authorize_path(mission_id: str, path: str) -> bool:
    root=PurePosixPath(namespace(mission_id))
    target=PurePosixPath(path.replace("\\","/"))
    try:
        target.relative_to(root)
        return ".." not in target.parts
    except ValueError:
        return False

def authorize_secret(mission_id: str, secret_name: str) -> bool:
    return secret_name.startswith(ALLOWED_SECRET_PREFIX+mission_id+"/")

def assert_isolated(mission_id: str, artifact_paths: list[str], secret_names: list[str]) -> None:
    bad_paths=[p for p in artifact_paths if not authorize_path(mission_id,p)]
    bad_secrets=[s for s in secret_names if not authorize_secret(mission_id,s)]
    if bad_paths or bad_secrets:
        raise PermissionError(f"CONTEXT_ISOLATION_VIOLATION:paths={bad_paths}:secrets={bad_secrets}")
