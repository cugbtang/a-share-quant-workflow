# K8s 部署清单（k8s/）

把"跑通的策略"做成可在 K8s 上定时跑批 + 监控的闭环。整体结构：

| 资源 | 文件 | 作用 |
|------|------|------|
| CronJob | `cronjob.yaml` | 工作日收盘后执行 `k8s/run_pipeline.sh`（数据 demo + 低波回测 + 降息事件研究），并把结果写入共享 PVC |
| Deployment | `strategy-deployment.yaml` | 常驻运行 `live/metrics_exporter.py`，暴露 `/metrics` |
| Service | `strategy-service.yaml` | 集群内暴露 exporter 的 8000 端口 |
| PVC | `pvc.yaml` | CronJob（写）与 exporter（读）共享 state 文件 |
| Kustomize | `kustomization.yaml` | 一键 `kubectl apply -k` |

## 1. 构建并推送镜像

```bash
# 在仓库根目录
docker build -t ghcr.io/cugbtang/a-share-quant-workflow:latest .
docker push ghcr.io/cugbtang/a-share-quant-workflow:latest
# 或改用你自己的镜像仓库，并同步修改各 yaml 中的 image 字段
```

> 镜像默认只装 `requirements.txt`（核心依赖，离线跑 demo + 低波回测）。
> 若要 CronJob 拉真实行情，需基于 `requirements-full.txt` 构建，或把
> `WESTOCK_BIN` 通过 Secret 注入（见下）。

## 2. 准备命名空间与 Secret（可选）

```bash
kubectl create namespace quant
# 若要用 westock-data 拉真实行情，把可执行入口写进 Secret（可选）
kubectl -n quant create secret generic quant-secrets \
  --from-literal=westock-bin="node /app/westock-data/scripts/index.js"
```

## 3. 部署

```bash
kubectl apply -k k8s/            # 等价于逐个 apply pvc/cronjob/deployment/service
```

## 4. 验证

```bash
# 触发一次手动跑批验证管道
kubectl -n quant create job --from=cronjob/quant-pipeline manual-run-$(date +%s)

# 查看 exporter 指标
kubectl -n quant port-forward svc/quant-exporter 8000:8000
curl localhost:8000/metrics | grep -E "marketdata_freshness|strategy_equity_return|order_fail|signal_latency"
```

## 5. 接入 Prometheus

在集群 Prometheus 的 `scrape_configs` 增加 job，目标为 `quant-exporter.quant.svc:8000`。
告警规则见仓库 `live/monitor/alerts.yml`（指标名与上方四个一致）。

## 注意事项

- CronJob 与 exporter 通过 PVC 共享 state 文件；默认 `ReadWriteOnce`，请保证二者
  **调度到同一节点**（节点亲和）或改用 `ReadWriteMany` 的 StorageClass（NFS/EFS/CFS）。
- `cronjob.yaml` 的 `schedule` 为 UTC；按集群实际时区调整（收盘后跑批）。
- 镜像地址、StorageClass、Secret 名均为占位，按你的环境替换。
- 本清单为工程骨架，未含真实账号、券商配置与完整风控；实盘前务必先在模拟盘跑通。
