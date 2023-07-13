# Cluster-level Runner


1. Install the promptops-runner statefulset and the required service account and role
    
    ```shell
    kubectl apply -f https://raw.githubusercontent.com/promptops/cli/main/config/k8s/all-readonly.yaml
    ```
        
2. Check the runner pod is running
    
    ```text
    ~ kubectl get pods -n promptops
    NAME                 READY   STATUS    RESTARTS   AGE
    promptops-runner-0   1/1     Running   0          21h
    ```
    
3. Obtain the pair code from the runner logs
    
    ```shell
    kubectl logs -f promptops-runner-0 -n promptops
    ```
    
4. Register in the Slack app
5. Test with "@PromptOps what are the pods in namespace promptops"

6. (Optional) To associate with IAM role
    1. Prerequisite EKS cluster with OIDC provider (https://docs.aws.amazon.com/eks/latest/userguide/enable-iam-roles-for-service-accounts.html)
    2. Run the script `eks/eks_aws_access.sh` which follow the guide here https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html starting from 2.b
    3. restart the pod to get new aws session
        ```shell
        kubectl delete pod promptops-runner-0 -n promptops
        ```