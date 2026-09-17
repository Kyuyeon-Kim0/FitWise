"""작업 측정기. 프로세스 기준이며 GPU/원격 API 자원은 제외합니다."""
import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

import psutil


@dataclass
class Operation:
    connection: object
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    processing_ms: float = 0

    def run_agent(self, agent_type, callback, product_id, user_id=None, size=None, top_level=True):
        started = time.perf_counter()
        result, error = None, None
        try:
            result = callback()
            return result
        except Exception as exc:
            error = type(exc).__name__
            raise
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            if top_level:
                self.processing_ms = elapsed
            self.connection.execute(
                """INSERT INTO agent_logs(request_id,agent_type,product_id,user_id,size,status,
                   processing_ms,result_json,error_type) VALUES (?,?,?,?,?,?,?,?,?)""",
                (self.request_id, agent_type, product_id, user_id, size, "error" if error else "success",
                 elapsed, json.dumps(result, ensure_ascii=False), error))
            self.connection.commit()


@contextmanager
def measure(connection, operation):
    if operation not in ("browse", "review", "fit"):
        raise ValueError("지원하지 않는 측정 작업입니다.")
    task = Operation(connection)
    process = psutil.Process()
    memory_before = process.memory_info().rss / 1024 ** 2
    process.cpu_percent(interval=None)
    started = time.perf_counter()
    status = "success"
    try:
        yield task
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = max((time.perf_counter() - started) * 1000, 0.001)
        logical_cpu_count = max(psutil.cpu_count(logical=True) or 1, 1)
        cpu_percent = min(max(process.cpu_percent(interval=None) / logical_cpu_count, 0.0), 100.0)
        memory_after = process.memory_info().rss / 1024 ** 2
        connection.execute(
            """INSERT INTO resource_logs(request_id,operation,cpu_percent,cpu_ms,memory_before_mb,
               memory_after_mb,memory_delta_mb,processing_ms,response_ms,status)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            # psutil의 프로세스 CPU 사용률을 전체 논리 코어 기준(0~100%)으로 정규화합니다.
            (task.request_id, operation, cpu_percent, 0.0, memory_before,
             memory_after, memory_after - memory_before,
             elapsed if operation == "browse" else task.processing_ms, elapsed, status))
        connection.commit()


def dashboard_data(connection):
    summary = [dict(row) for row in connection.execute(
        """SELECT operation,COUNT(*) AS count,AVG(cpu_percent) AS cpu_percent,
           AVG(memory_after_mb) AS memory_mb,AVG(memory_delta_mb) AS memory_delta_mb,
           AVG(processing_ms) AS processing_ms,AVG(response_ms) AS response_ms
           FROM resource_logs WHERE status='success' GROUP BY operation""")]
    resources = [dict(row) for row in connection.execute("SELECT * FROM resource_logs ORDER BY id DESC LIMIT 50")]
    agents = [dict(row) for row in connection.execute(
        """SELECT a.id,a.request_id,a.agent_type,a.status,a.processing_ms,a.created_at,p.name AS product_name
           FROM agent_logs a LEFT JOIN products p ON p.id=a.product_id ORDER BY a.id DESC LIMIT 30""")]
    counts = dict(connection.execute(
        "SELECT COUNT(*) AS total,COALESCE(SUM(status='error'),0) AS errors FROM agent_logs").fetchone())
    return {"summary": summary, "resources": resources, "agents": agents, "counts": counts}
