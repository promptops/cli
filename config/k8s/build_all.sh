> all.yaml
cat namespace.yaml >> all.yaml
echo "---" >> all.yaml
cat clusterrole.yaml >> all.yaml
echo "---" >> all.yaml
cat serviceaccount.yaml >> all.yaml
echo "---" >> all.yaml
cat rbac.yaml >> all.yaml
echo "---" >> all-readonly.yaml
echo aws.yaml >> all-readonly.yaml
echo "---" >> all.yaml
cat statefulset.yaml >> all.yaml

> all-readonly.yaml
cat namespace.yaml >> all-readonly.yaml
echo "---" >> all-readonly.yaml
cat clusterrole-readonly.yaml >> all-readonly.yaml
echo "---" >> all-readonly.yaml
cat serviceaccount.yaml >> all-readonly.yaml
echo "---" >> all-readonly.yaml
cat rbac.yaml >> all-readonly.yaml
echo "---" >> all-readonly.yaml
echo aws.yaml >> all-readonly.yaml
echo "---" >> all-readonly.yaml
cat statefulset.yaml >> all-readonly.yaml
