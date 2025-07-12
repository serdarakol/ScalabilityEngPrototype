import json
import pandas as pd
import matplotlib.pyplot as plt
import os

LOG_FILE = "./src/client/responses.log"
SUMMARY_OUTPUT = "summary_1st_experiment.json"
PLOT_DIR = "plots/first_experiment"
os.makedirs(PLOT_DIR, exist_ok=True)

def parse_line(line):
    try:
        return json.loads(line)
    except:
        return None

with open(LOG_FILE, 'r') as f:
    data = [parse_line(line) for line in f if line.strip()]

df = pd.DataFrame([d for d in data if d is not None])

def extract_response_fields(row):
    if pd.notnull(row.get("response")):
        resp = row["response"]
        return {
            "pod": resp.get("pod", "unknown"),
            "fromCache": resp.get("fromCache", False)
        }
    elif pd.notnull(row.get("error")):
        try:
            err = json.loads(row["error"])
            resp = err.get("response", {})
            return {
                "pod": resp.get("pod", "unknown"),
                "fromCache": False,
                "error_code": err.get("code", ""),
                "error_status": resp.get("status", None)
            }
        except:
            return {"pod": "unknown", "fromCache": False}
    return {"pod": "unknown", "fromCache": False}

extracted = df.apply(extract_response_fields, axis=1, result_type='expand')
df = pd.concat([df, extracted], axis=1)

total_requests = len(df)
total_429s = df['error'].dropna().apply(lambda x: '429' in x).sum()
total_cache_hits = df['fromCache'].sum()

req_per_client = df.groupby("client").size()

df["is_429"] = df["error"].apply(lambda x: "429" in x if pd.notnull(x) else False)
err_429_per_client = df[df["is_429"]].groupby("client").size()

err_429_per_pod = df[df["is_429"]].groupby("pod").size()

pod_cache_stats = df.groupby("pod")["fromCache"].agg(["count", "sum"])
pod_cache_stats["hit_rate"] = pod_cache_stats["sum"] / pod_cache_stats["count"]

cache_hit_rate = total_cache_hits / total_requests if total_requests else 0

summary = {
    "total_requests": total_requests,
    "total_429_errors": int(total_429s),
    "cache_hit_rate": round(cache_hit_rate, 4),
    "requests_per_client": req_per_client.to_dict(),
    "429s_per_client": err_429_per_client.to_dict(),
    "429s_per_pod": err_429_per_pod.to_dict(),
    "cache_stats_per_pod": pod_cache_stats[["count", "sum", "hit_rate"]].rename(
        columns={"count": "total", "sum": "hits"}).round(4).to_dict(orient="index")
}

with open(SUMMARY_OUTPUT, "w") as f:
    json.dump(summary, f, indent=4)

print(f"Summary written to {SUMMARY_OUTPUT}")

def plot_bar(data_dict, title, filename, xlabel="Key", ylabel="Count"):
    plt.figure()
    keys, values = zip(*data_dict.items()) if data_dict else ([], [])
    plt.bar(keys, values)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, filename))
    plt.close()

plot_bar(req_per_client.to_dict(), "Total Requests per Client", "requests_per_client.png")
plot_bar(err_429_per_client.to_dict(), "429 Errors per Client", "429s_per_client.png")
plot_bar(err_429_per_pod.to_dict(), "429 Errors per Pod", "429s_per_pod.png")
plot_bar(pod_cache_stats["hit_rate"].round(2).to_dict(), "Cache Hit Rate per Pod", "cache_hit_rate_per_pod.png", ylabel="Hit Rate")

print(f"Plots saved to '{PLOT_DIR}/'")
