set -e

read -p 'Please enter the cluster: ' CLUSTER
read -p 'Please enter the region: ' AWS_REGION

ROLE_NAME=promptops-runner-$CLUSTER

account_id=$(aws sts get-caller-identity --query "Account" --output text)
echo "account id: $account_id"
oidc_provider=$(aws eks describe-cluster --name $CLUSTER --region $AWS_REGION --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")
echo "oidc provider: $oidc_provider"

namespace=promptops
service_account=promptops-runner

cat >trust-relationship.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$account_id:oidc-provider/$oidc_provider"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "$oidc_provider:aud": "sts.amazonaws.com",
          "$oidc_provider:sub": "system:serviceaccount:$namespace:$service_account"
        }
      }
    }
  ]
}
EOF

echo "creating role $ROLE_NAME"
read -p 'Press enter to continue'
aws iam create-role --role-name $ROLE_NAME --assume-role-policy-document file://trust-relationship.json --description "allow promptops to run AWS scripts" --no-cli-pager
aws iam attach-role-policy --role-name $ROLE_NAME --policy-arn=arn:aws:iam::aws:policy/ReadOnlyAccess --no-cli-pager
echo "done!"

echo "Please annotate the service account with the following:"
echo "kubectl annotate serviceaccount -n $namespace $service_account eks.amazonaws.com/role-arn=arn:aws:iam::$account_id:role/$ROLE_NAME"
