# Memosphere Architecture Comparison

| Option              | Cost (MVP) | Complexity | Scalability | Future-Proof | Best For                  |
|---------------------|------------|------------|-------------|---------------|---------------------------|
| Serverless          | ✅ Lowest  | ✅ Minimal | ✅ Auto      | ⚠️ Limited     | Solo devs, MVPs           |
| Kubernetes on EC2   | ⚠️ Low–Med | ⚠️ Moderate| ✅ Manual    | ✅ Flexible    | Devs wanting control      |
| Amazon EKS          | ❌ High    | ❌ Complex | ✅ Enterprise| ✅ Very High   | Teams, production scale   |


-> Chose Kubernetes on EC2 because it is cheap and future-proof