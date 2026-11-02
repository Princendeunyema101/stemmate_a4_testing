class SessionPlan:
    def __init__(self, title, content=""):
        self.title = title
        self.content = content

class SyncQueueItem:
    def __init__(self, id, data):
        self.id = id
        self.data = data
        self.retry_count = 0
        self.status = "PENDING"

class SessionPlanService:
    def validate(self, plan):
        if not plan.title:
            raise ValueError("Title is required")
        return True

class ConflictResolver:
    def merge(self, local, remote):
        if "title" in local and "title" in remote and local["title"] != remote["title"]:
            return {"status": "CONFLICT_MANUAL"}
        merged_steps = list(set(local.get("steps", []) + remote.get("steps", [])))
        return {"steps": merged_steps, "status": "MERGED"}

class RemoteSyncGateway:
    @staticmethod
    def send(item):
        pass

class SyncCoordinator:
    def sync_item(self, item):
        try:
            RemoteSyncGateway.send(item)
            item.status = "SYNCED"
        except Exception:
            item.retry_count += 1
            item.status = "RETRY_SCHEDULED"

class AccessGuard:
    def __init__(self):
        self._authenticated = False

    def signIn(self, username, password):
        if username == "prince_nde" and password == "secure_pass":
            self._authenticated = True
            return True
        return False

    def is_authenticated(self):
        return self._authenticated
