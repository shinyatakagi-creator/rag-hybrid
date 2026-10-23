# Checkpoint 4: label 30 citation pairs

For each item, read the sentence and the excerpt it cites, and decide from the excerpt ALONE (not from what you know about Kubernetes) whether the excerpt supports the sentence:

- **supported**: the excerpt states the sentence's claims or directly implies them (paraphrase and equivalent numbers count);
- **partial**: some of the claims are supported, others are not (or go beyond the excerpt);
- **unsupported**: the excerpt does not support the sentence, or contradicts it.

Write one label per row in `eval/checkpoint4/my_labels.csv` (columns `id,label,note`). Do not open the key file until you have saved all 30 labels.

## L01

**Sentence:** For example, when disk resources are starved, it removes unused container images.

**Cited excerpt:**

````text
Self healing behavior
The kubelet attempts to [reclaim node-level resources](#reclaim-node-resources)
before it terminates end-user pods. For example, it removes unused container
images when disk resources are starved.  
If the pods are managed by a workload
management object (such as StatefulSet
or Deployment) that
replaces failed pods, the control plane (`kube-controller-manager`) creates new
pods in place of the evicted pods.

If you are running a [static pod](/docs/concepts/workloads/pods/#static-pods)
on a node that is under resource pressure, the kubelet may evict that static
Pod. The kubelet then tries to create a replacement, because static Pods always
represent an intent to run a Pod on that node.  
The kubelet takes the _priority_ of the static pod into account when creating
a replacement. If the static pod manifest specifies a low priority, and there
are higher-priority Pods defined within the cluster's control plane, and the
node is under resource pressure, the kubelet may not be able to make room for
that static pod. The kubelet continues to attempt to run all static pods even
when there is resource pressure on a node.
````

## L02

**Sentence:** Rather than tracking a user's last applied state as the legacy `last-applied` annotation does, Server-Side Apply tracks an object's field management, so information about which field manager manages each field becomes available.

**Cited excerpt:**

````text
The Kubernetes API server tracks _managed fields_ for all newly created objects.  
When trying to apply an object, fields that have a different value and are owned by
another [manager](#managers) will result in a [conflict](#conflicts). This is done
in order to signal that the operation might undo another collaborator's changes.
Writes to objects with managed fields can be forced, in which case the value of any
conflicted field will be overridden, and the ownership will be transferred.  
Whenever a field's value does change, ownership moves from its current manager to the
manager making the change.  
For a user to manage a field, in the Server-Side Apply sense, means that the
user relies on and expects the value of the field not to change. The user who
last made an assertion about the value of a field will be recorded as the
current field manager. This can be done by changing the field manager
details explicitly using HTTP `POST` (**create**), `PUT` (**update**), or non-apply
`PATCH` (**patch**). You can also declare and record a field manager
by including a value for that field in a Server-Side Apply operation.  
A Server-Side Apply **patch** request requires the client to provide its identity
as a [field manager](#managers). When using Server-Side Apply, trying to change a
field that is controlled by a different manager results in a rejected
request unless the client forces an override.
For details of overrides, see [Conflicts](#conflicts).  
When two or more appliers set a field to the same value, they share ownership of
that field. Any subsequent attempt to change the value of the shared field, by any of
the appliers, results in a conflict. Shared field owners may give up ownership
of a field by making a Server-Side Apply **patch** request that doesn't include
that field.  
Field management details are stored in a `managedFields` field that is part of an
object's [`metadata`](/docs/reference/kubernetes-api/common-definitions/object-meta/).  
If you remove a field from a manifest and apply that manifest, Server-Side
Apply checks if there are any other field managers that also own the field.
If the field is not owned by any other field managers, it is either deleted
from the live object or reset to its default value, if it has one.
The same rule applies to associative list or map items.  
Compared to the (legacy)
[`kubectl.kubernetes.io/last-applied-configuration`](/docs/reference/labels-annotations-taints/#kubectl-kubernetes-io-last-applied-configuration)
annotation managed by `kubectl`, Server-Side Apply uses a more declarative
````

## L03

**Sentence:** Boundaries within a namespace should be considered weak, so namespaces should be used to separate resources requiring different levels of trust or tenancy.

**Cited excerpt:**

````text
Permission to create workloads (either Pods, or
[workload resources](/docs/concepts/workloads/controllers/) that manage Pods) in a namespace
implicitly grants access to many other resources in that namespace, such as Secrets, ConfigMaps, and
PersistentVolumes that can be mounted in Pods. Additionally, since Pods can run as any
[ServiceAccount](/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.  
Users who can run privileged Pods can use that access to gain node access and potentially to
further elevate their privileges. Where you do not fully trust a user or other principal
with the ability to create suitably secure and isolated Pods, you should enforce either the
**Baseline** or **Restricted** Pod Security Standard.
You can use [Pod Security admission](/docs/concepts/security/pod-security-admission/)
or other (third party) mechanisms to implement that enforcement.  
For these reasons, namespaces should be used to separate resources requiring different levels of
trust or tenancy. It is still considered best practice to follow [least privilege](#least-privilege)
principles and assign the minimum set of permissions, but boundaries within a namespace should be
considered weak.
````

## L04

**Sentence:** Components that specify `--cloud-provider=external` add the `node.cloudprovider.kubernetes.io/uninitialized` taint with a `NoSchedule` effect during initialization.

**Cited excerpt:**

````text
Successfully running cloud-controller-manager requires some changes to your cluster configuration.  
* `kubelet` and `kube-controller-manager` must be set according to the
user's usage of external CCM. If the user has an external CCM (not the internal cloud
controller loops in the Kubernetes Controller Manager), then `--cloud-provider=external`
must be specified. Otherwise, it should not be specified.  
Keep in mind that setting up your cluster to use cloud controller manager will
change your cluster behaviour in a few ways:  
* Components that specify `--cloud-provider=external` will add a taint
`node.cloudprovider.kubernetes.io/uninitialized` with an effect `NoSchedule`
during initialization. This marks the node as needing a second initialization
from an external controller before it can be scheduled work. Note that in the
event that cloud controller manager is not available, new nodes in the cluster
will be left unschedulable. The taint is important since the scheduler may
require cloud specific information about nodes such as their region or type
(high cpu, gpu, high memory, spot instance, etc).
* cloud information about nodes in the cluster will no longer be retrieved using
local metadata, but instead all API calls to retrieve node information will go
through cloud controller manager. This may mean you can restrict access to your
cloud API on the kubelets for better security. For larger clusters you may want
to consider if cloud controller manager will hit rate limits since it is now
responsible for almost all API calls to your cloud from within the cluster.  
The cloud controller manager can implement:  
* Node controller - responsible for updating kubernetes nodes using cloud APIs
and deleting kubernetes nodes that were deleted on your cloud.
* Service controller - responsible for loadbalancers on your cloud against
services of type LoadBalancer.
* Route controller - responsible for setting up network routes on your cloud
* any other features you would like to implement if you are running an out-of-tree provider.
````

## L05

**Sentence:** The Node stays marked this way until a controller from the cloud-controller-manager initializes it, and then the taint is removed.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.18 [stable]  
The node controller automatically taints a Node when certain conditions
are true. The following taints are built in:  
* `node.kubernetes.io/not-ready`: Node is not ready. This corresponds to
the NodeCondition `Ready` being "`False`".
* `node.kubernetes.io/unreachable`: Node is unreachable from the node
controller. This corresponds to the NodeCondition `Ready` being "`Unknown`".
* `node.kubernetes.io/memory-pressure`: Node has memory pressure.
* `node.kubernetes.io/disk-pressure`: Node has disk pressure.
* `node.kubernetes.io/pid-pressure`: Node has PID pressure.
* `node.kubernetes.io/network-unavailable`: Node's network is unavailable.
* `node.kubernetes.io/unschedulable`: Node is unschedulable.
* `node.cloudprovider.kubernetes.io/uninitialized`: When the kubelet is started
with an "external" cloud provider, this taint is set on a node to mark it
as unusable. After a controller from the cloud-controller-manager initializes
this node, the kubelet removes this taint.  
In case a node is to be drained, the node controller or the kubelet adds relevant taints
with `NoExecute` effect. This effect is added by default for the
`node.kubernetes.io/not-ready` and `node.kubernetes.io/unreachable` taints.
If the fault condition returns to normal, the kubelet or node
controller can remove the relevant taint(s).  
In some cases when the node is unreachable, the API server is unable to communicate
with the kubelet on the node. The decision to delete the pods cannot be communicated to
the kubelet until communication with the API server is re-established. In the meantime,
the pods that are scheduled for deletion may continue to run on the partitioned node.  
Note:
The control plane limits the rate of adding new taints to nodes. This rate limiting
manages the number of evictions that are triggered when many nodes become unreachable at
once (for example: if there is a network disruption).  
You can specify `tolerationSeconds` for a Pod to define how long that Pod stays bound
to a failing or unresponsive Node.  
For example, you might want to keep an application with a lot of local state
bound to node for a long time in the event of network partition, hoping
that the partition will recover and thus the pod eviction can be avoided.
The toleration you set for that Pod might look like:  

```yaml
tolerations:
- key: "node.kubernetes.io/unreachable"
operator: "Exists"
effect: "NoExecute"
tolerationSeconds: 6000
```  
````

## L06

**Sentence:** Users who can run privileged Pods can use that access to gain node access and potentially elevate their privileges further, and any containers running with privileged: true on a node can access all Secrets used on that node.

**Cited excerpt:**

````text
Although ConfigMap and Secret work similarly, Kubernetes applies some additional
protection for Secret objects.  
Secrets often hold values that span a spectrum of importance, many of which can
cause escalations within Kubernetes (e.g. service account tokens) and to
external systems. Even if an individual app can reason about the power of the
Secrets it expects to interact with, other apps within the same namespace can
render those assumptions invalid.  
Authorization configuration affects how Secret data can be accessed within a namespace.
For example, granting **list** or **watch** permissions on Secrets allows a subject
to read all Secret data in that namespace, not only the Secrets explicitly
referenced by its Pods. Restrict access to the minimum set of permissions
required for a workload to function, and avoid granting broad roles such as
`cluster-admin` unless required for administrative purposes.  
Also see the [Authorization documentation](/docs/reference/access-authn-authz/rbac/).  
A Secret is only sent to a node if a Pod on that node requires it.
For mounting Secrets into Pods, the kubelet stores a copy of the data into a `tmpfs`
so that the confidential data is not written to durable storage.
Once the Pod that depends on the Secret is deleted, the kubelet deletes its local copy
of the confidential data from the Secret.  
There may be several containers in a Pod. By default, containers you define
only have access to the default ServiceAccount and its related Secret.
You must explicitly define environment variables or map a volume into a
container in order to provide access to any other Secret.  
There may be Secrets for several Pods on the same node. However, only the
Secrets that a Pod requests are potentially visible within its containers.
Therefore, one Pod does not have access to the Secrets of another Pod.

Configure least-privilege access to Secrets
To enhance the security measures around Secrets, use separate namespaces to isolate access to mounted secrets.  
Warning:
Any containers that run with `privileged: true` on a node can access all
Secrets used on that node.
````

## L07

**Sentence:** You also need to pass the binary's signature and certificate to `cosign verify-blob` using `--signature` (the `.sig` file) and `--certificate` (the `.cert` file), which you download alongside the binary.

**Cited excerpt:**

````text
The Kubernetes release process signs all binary artifacts (tarballs, SPDX files,
standalone binaries) by using cosign's keyless signing. To verify a particular
binary, retrieve it together with its signature and certificate:  
```bash
URL=https://dl.k8s.io/release/v/bin/linux/amd64
BINARY=kubectl

FILES=(
"$BINARY"
"$BINARY.sig"
"$BINARY.cert"
)

for FILE in "${FILES[@]}"; do
curl -sSfL --retry 3 --retry-delay 3 "$URL/$FILE" -o "$FILE"
done
```  
Then verify the blob by using `cosign verify-blob`:  
```shell
cosign verify-blob "$BINARY" \
--signature "$BINARY".sig \
--certificate "$BINARY".cert \
--certificate-identity krel-staging@k8s-releng-prod.iam.gserviceaccount.com \
--certificate-oidc-issuer https://accounts.google.com
```  
Note:
Cosign 2.0 requires the `--certificate-identity` and `--certificate-oidc-issuer` options.  
To learn more about keyless signing, please refer to [Keyless Signatures](https://docs.sigstore.dev/cosign/signing/overview/).  
Previous versions of Cosign required that you set `COSIGN_EXPERIMENTAL=1`.  
For additional information, please refer to the [sigstore Blog](https://blog.sigstore.dev/cosign-2-0-released/)
````

## L08

**Sentence:** Permission to create workloads in a namespace implicitly grants access to other resources in that namespace, such as Secrets, ConfigMaps, and PersistentVolumes that can be mounted in Pods.

**Cited excerpt:**

````text
Permission to create workloads (either Pods, or
[workload resources](/docs/concepts/workloads/controllers/) that manage Pods) in a namespace
implicitly grants access to many other resources in that namespace, such as Secrets, ConfigMaps, and
PersistentVolumes that can be mounted in Pods. Additionally, since Pods can run as any
[ServiceAccount](/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.  
Users who can run privileged Pods can use that access to gain node access and potentially to
further elevate their privileges. Where you do not fully trust a user or other principal
with the ability to create suitably secure and isolated Pods, you should enforce either the
**Baseline** or **Restricted** Pod Security Standard.
You can use [Pod Security admission](/docs/concepts/security/pod-security-admission/)
or other (third party) mechanisms to implement that enforcement.  
For these reasons, namespaces should be used to separate resources requiring different levels of
trust or tenancy. It is still considered best practice to follow [least privilege](#least-privilege)
principles and assign the minimum set of permissions, but boundaries within a namespace should be
considered weak.
````

## L09

**Sentence:** You must also supply the binary's signature with `--signature` and its certificate with `--certificate`, which you download along with the binary as `$BINARY.sig` and `$BINARY.cert`.

**Cited excerpt:**

````text
The Kubernetes release process signs all binary artifacts (tarballs, SPDX files,
standalone binaries) by using cosign's keyless signing. To verify a particular
binary, retrieve it together with its signature and certificate:  
```bash
URL=https://dl.k8s.io/release/v/bin/linux/amd64
BINARY=kubectl

FILES=(
"$BINARY"
"$BINARY.sig"
"$BINARY.cert"
)

for FILE in "${FILES[@]}"; do
curl -sSfL --retry 3 --retry-delay 3 "$URL/$FILE" -o "$FILE"
done
```  
Then verify the blob by using `cosign verify-blob`:  
```shell
cosign verify-blob "$BINARY" \
--signature "$BINARY".sig \
--certificate "$BINARY".cert \
--certificate-identity krel-staging@k8s-releng-prod.iam.gserviceaccount.com \
--certificate-oidc-issuer https://accounts.google.com
```  
Note:
Cosign 2.0 requires the `--certificate-identity` and `--certificate-oidc-issuer` options.  
To learn more about keyless signing, please refer to [Keyless Signatures](https://docs.sigstore.dev/cosign/signing/overview/).  
Previous versions of Cosign required that you set `COSIGN_EXPERIMENTAL=1`.  
For additional information, please refer to the [sigstore Blog](https://blog.sigstore.dev/cosign-2-0-released/)
````

## L10

**Sentence:** The newer approach is Server-Side Apply, which is meant as a replacement for the original client-side implementation of `kubectl apply`.

**Cited excerpt:**

````text
Server-Side Apply is meant both as a replacement for the original client-side
implementation of the `kubectl apply` subcommand, and as simple and effective
mechanism for controllers
to enact their changes.  
Compared to the `last-applied` annotation managed by `kubectl`, Server-Side
Apply uses a more declarative approach, which tracks an object's field management,
rather than a user's last applied state. This means that as a side effect of
using Server-Side Apply, information about which field manager manages each
field in an object also becomes available.  
A consequence of the conflict detection and resolution implemented by Server-Side
Apply is that an applier always has up to date field values in their local
state. If they don't, they get a conflict the next time they apply. Any of the
three options to resolve conflicts results in the applied configuration being an
up to date subset of the object on the server's fields.  
This is different from Client-Side Apply, where outdated values which have been
overwritten by other users are left in an applier's local config. These values
only become accurate when the user updates that specific field, if ever, and an
applier has no way of knowing whether their next apply will overwrite other
users' changes.  
Another difference is that an applier using Client-Side Apply is unable to
change the API version they are using, but Server-Side Apply supports this use
case.
````

## L11

**Sentence:** If any PreBind plugin returns an error, the Pod is rejected and returned to the scheduling queue.

**Cited excerpt:**

````text
PreBind {#pre-bind}
These plugins are used to perform any work required before a Pod is bound. For
example, a pre-bind plugin may provision a network volume and mount it on the
target node before allowing the Pod to run there.  
If any PreBind plugin returns an error, the Pod is [rejected](#reserve) and
returned to the scheduling queue.

These plugins are used to bind a Pod to a Node. Bind plugins will not be called
until all PreBind plugins have completed. Each bind plugin is called in the
configured order. A bind plugin may choose whether or not to handle the given
Pod. If a bind plugin chooses to handle a Pod, **the remaining bind plugins are
skipped**.

PostBind {#post-bind}
This is an informational interface. Post-bind plugins are called after a
Pod is successfully bound. This is the end of a binding cycle, and can be used
to clean up associated resources.
````

## L12

**Sentence:** Controllers copy the schedulingPolicy from the template into each CompositePodGroup they create, and minGroupCount in a CompositePodGroupTemplate is immutable.

**Cited excerpt:**

````text
API structure
A `CompositePodGroup` consists of a `spec` that defines the desired scheduling behavior
for its child groups, and a `status` subresource.

Each `CompositePodGroup` carries a [scheduling policy](/docs/concepts/workloads/workload-api/policies/)
(`basic` or `gang`) in `spec.schedulingPolicy`. When a workload controller creates a
`CompositePodGroup`, this policy is copied from the `Workload`'s `CompositePodGroupTemplate`
at creation time.  
For a `gang` policy on a `CompositePodGroup`, the `minGroupCount` field specifies the
minimum number of child groups that must be schedulable simultaneously:  
```yaml
spec:
schedulingPolicy:
gang:
minGroupCount: 2
```
````

## L13

**Sentence:** When a container is created without a memory request or limit in a namespace that has a LimitRange, the cluster applies the default memory request and limit from that LimitRange to the container.

**Cited excerpt:**

````text
If your namespace has a memory resource quota
configured,
it is helpful to have a default value in place for memory limit.
Here are three of the restrictions that a resource quota imposes on a namespace:  
* For every Pod that runs in the namespace, the Pod and each of its containers must have a memory limit.
(If you specify a memory limit for every container in a Pod, Kubernetes can infer the Pod-level memory
limit by adding up the limits for its containers).
* Memory limits apply a resource reservation on the node where the Pod in question is scheduled.
The total amount of memory reserved for all Pods in the namespace must not exceed a specified limit.
* The total amount of memory actually used by all Pods in the namespace must also not exceed a specified limit.  
When you add a LimitRange:  
If any Pod in that namespace that includes a container does not specify its own memory limit,
the control plane applies the default memory limit to that container, and the Pod can be
allowed to run in a namespace that is restricted by a memory ResourceQuota.
````

## L14

**Sentence:** Each string in the `schedulingGates` list is treated as a criterion that the Pod must satisfy before it is considered schedulable.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.30 [stable]  
Pods were considered ready for scheduling once created. Kubernetes scheduler
does its due diligence to find nodes to place all pending Pods. However, in a
real-world case, some Pods may stay in a "miss-essential-resources" state for a long period.
These Pods actually churn the scheduler (and downstream integrators like Cluster AutoScaler)
in an unnecessary manner.  
By specifying/removing a Pod's `.spec.schedulingGates`, you can control when a Pod is ready
to be considered for scheduling.

Configuring Pod schedulingGates
The `schedulingGates` field contains a list of strings, and each string literal is perceived as a
criteria that Pod should be satisfied before considered schedulable. This field can be initialized
only when a Pod is created (either by the client, or mutated during admission). After creation,
each schedulingGate can be removed in arbitrary order, but addition of a new scheduling gate is disallowed.  
Figure: Figure. Pod SchedulingGates
````

## L15

**Sentence:** Those packet filtering rules direct DNS queries to a local Pod that is now unhealthy, so lookups fail.

**Cited excerpt:**

````text
The `node-local-dns` Pods use memory for storing cache entries and processing queries.
Since they do not watch Kubernetes objects, the cluster size or the number of Services / EndpointSlices do not directly affect memory usage. Memory usage is influenced by the DNS query pattern.
From [CoreDNS docs](https://github.com/coredns/deployment/blob/master/kubernetes/Scaling_CoreDNS.md),
> The default cache size is 10000 entries, which uses about 30 MB when completely filled.  
This would be the memory usage for each server block (if the cache gets completely filled).
Memory usage can be reduced by specifying smaller cache sizes.  
The number of concurrent queries is linked to the memory demand, because each extra
goroutine used for handling a query requires an amount of memory. You can set an upper limit
using the `max_concurrent` option in the forward plugin.  
If a `node-local-dns` Pod attempts to use more memory than is available (because of total system
resources, or because of a configured
[resource limit](/docs/concepts/configuration/manage-resources-containers/)), the operating system
may shut down that pod's container.
If this happens, the container that is terminated (“OOMKilled”) does not clean up the custom
packet filtering rules that it previously added during startup.
The `node-local-dns` container should get restarted (since managed as part of a DaemonSet), but this
will lead to a brief DNS downtime each time that the container fails: the packet filtering rules direct
DNS queries to a local Pod that is unhealthy.  
You can determine a suitable memory limit by running node-local-dns pods without a limit and
measuring the peak usage. You can also set up and use a
[VerticalPodAutoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
in _recommender mode_, and then check its recommendations.
````

## L16

**Sentence:** If `--peer-advertise-ip` and `--peer-advertise-port` are unspecified, peers use the value from `--advertise-address` or `--bind-address` of the kube-apiserver.

**Cited excerpt:**

````text
To set the network location of a kube-apiserver that peers will use to proxy requests, use the
`--peer-advertise-ip` and `--peer-advertise-port` command line arguments to kube-apiserver or specify
these fields in the API server configuration file.
If these flags are unspecified, peers will use the value from either `--advertise-address` or
`--bind-address` command line argument to the kube-apiserver.
If those too, are unset, the host's default interface is used.
````

## L17

**Sentence:** No, they do not matter: the scheduler only considers nodes that have all of the topologySpreadConstraints[*].topologyKey labels present at the same time, and nodes missing any of them are bypassed.

**Cited excerpt:**

````text
There are some implicit conventions worth noting here:  
- Only the Pods holding the same namespace as the incoming Pod can be matching candidates.  
- The scheduler only considers nodes that have all `topologySpreadConstraints[*].topologyKey` present at the same time.
Nodes missing any of these `topologyKeys` are bypassed. This implies that:  
1. any Pods located on those bypassed nodes do not impact `maxSkew` calculation - in the
above [example](#example-conflicting-topologyspreadconstraints), suppose the node `node1`
does not have a label "zone", then the 2 Pods will
be disregarded, hence the incoming Pod will be scheduled into zone `A`.
2. the incoming Pod has no chances to be scheduled onto this kind of nodes -
in the above example, suppose a node `node5` has the **mistyped** label `zone-typo: zoneC`
(and no `zone` label set). After node `node5` joins the cluster, it will be bypassed and
Pods for this workload aren't scheduled there.  
- Be aware of what will happen if the incoming Pod's
`topologySpreadConstraints[*].labelSelector` doesn't match its own labels. In the
above example, if you remove the incoming Pod's labels, it can still be placed onto
nodes in zone `B`, since the constraints are still satisfied. However, after that
placement, the degree of imbalance of the cluster remains unchanged - it's still zone `A`
having 2 Pods labeled as `foo: bar`, and zone `B` having 1 Pod labeled as
`foo: bar`. If this is not what you expect, update the workload's
`topologySpreadConstraints[*].labelSelector` to match the labels in the pod template.
````

## L18

**Sentence:** Because Pods can run as any ServiceAccount, permission to create workloads also implicitly grants the API access levels of any service account in that namespace.

**Cited excerpt:**

````text
Permission to create workloads (either Pods, or
[workload resources](/docs/concepts/workloads/controllers/) that manage Pods) in a namespace
implicitly grants access to many other resources in that namespace, such as Secrets, ConfigMaps, and
PersistentVolumes that can be mounted in Pods. Additionally, since Pods can run as any
[ServiceAccount](/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.  
Users who can run privileged Pods can use that access to gain node access and potentially to
further elevate their privileges. Where you do not fully trust a user or other principal
with the ability to create suitably secure and isolated Pods, you should enforce either the
**Baseline** or **Restricted** Pod Security Standard.
You can use [Pod Security admission](/docs/concepts/security/pod-security-admission/)
or other (third party) mechanisms to implement that enforcement.  
For these reasons, namespaces should be used to separate resources requiring different levels of
trust or tenancy. It is still considered best practice to follow [least privilege](#least-privilege)
principles and assign the minimum set of permissions, but boundaries within a namespace should be
considered weak.
````

## L19

**Sentence:** preBind plugins perform any work required before a Pod is bound.

**Cited excerpt:**

````text
Scheduling happens in a series of stages that are exposed through the following
extension points:  
1. `queueSort`: These plugins provide an ordering function that is used to
sort pending Pods in the scheduling queue. Exactly one queue sort plugin
may be enabled at a time.
1. `placementGenerate`: These plugins generate potential placements (sets of
nodes) where a considered PodGroup could be scheduled. This extension point
is only applicable to PodGroup scheduling and requires Workload scheduling
to be enabled.
1. `placementScore`: These plugins score the placements proposed by
`placementGenerate`, to pick the optimal placement for the considered
PodGroup.
1. `preFilter`: These plugins are used to pre-process or check information
about a Pod or the cluster before filtering. They can mark a pod as
unschedulable.
1. `filter`: These plugins are the equivalent of Predicates in a scheduling
Policy and are used to filter out nodes that can not run the Pod. Filters
are called in the configured order. A pod is marked as unschedulable if no
nodes pass all the filters.
1. `postFilter`: These plugins are called in their configured order when no
feasible nodes were found for the pod. If any `postFilter` plugin marks the
Pod _schedulable_, the remaining plugins are not called. These plugins are not
applicable for pods being scheduled as part of PodGroup scheduling.
1. `podGroupPostFilter`: These plugins are called in their configured order when no
feasible placement is found for the pod group. If any `podGroupPostFilter` plugin marks
the pod group as _schedulable_, the remaining plugins are not called. This extension point
is only applicable to PodGroup scheduling and requires Workload scheduling
to be enabled.
1. `preScore`: This is an informational extension point that can be used
for doing pre-scoring work.
1. `score`: These plugins provide a score to each node that has passed the
filtering phase. The scheduler will then select the node with the highest
weighted scores sum.
1. `reserve`: This is an informational extension point that notifies plugins
when resources have been reserved for a given Pod. Plugins also implement an
`Unreserve` call that gets called in the case of failure during or after
`Reserve`.
1. `permit`: These plugins can prevent or delay the binding of a Pod.
1. `preBind`: These plugins perform any work required before a Pod is bound.
1. `bind`: The plugins bind a Pod to a Node. `bind` plugins are called in order
and once one has done the binding, the remaining plugins are skipped. At
least one bind plugin is required.
1. `postBind`: This is an informational extension point that is called after
````

## L20

**Sentence:** If you delete the Job while these Pods are running, Kubernetes uses the owner references (not labels) to determine which Pods in the cluster need cleanup.

**Cited excerpt:**

````text
Like labels,
[owner references](/docs/concepts/overview/working-with-objects/owners-dependents/)
describe the relationships between objects in Kubernetes, but are used for a
different purpose. When a
controller manages objects
like Pods, it uses labels to track changes to groups of related objects. For
example, when a Job creates one or
more Pods, the Job controller applies labels to those pods and tracks changes to
any Pods in the cluster with the same label.  
The Job controller also adds *owner references* to those Pods, pointing at the
Job that created the Pods. If you delete the Job while these Pods are running,
Kubernetes uses the owner references (not labels) to determine which Pods in the
cluster need cleanup.  
Kubernetes also processes finalizers when it identifies owner references on a
resource targeted for deletion.  
In some situations, finalizers can block the deletion of dependent objects,
which can cause the targeted owner object to remain for
longer than expected without being fully deleted. In these situations, you
should check finalizers and owner references on the target owner and dependent
objects to troubleshoot the cause.  
Note:
In cases where objects are stuck in a deleting state, avoid manually
removing finalizers to allow deletion to continue. Finalizers are usually added
to resources for a reason, so forcefully removing them can lead to issues in
your cluster. This should only be done when the purpose of the finalizer is
understood and is accomplished in another way (for example, manually cleaning
up some dependent object).
````

## L21

**Sentence:** Users who can run privileged Pods can use that access to gain node access and potentially elevate their privileges further, and any containers running with privileged: true on a node can access all Secrets used on that node.

**Cited excerpt:**

````text
Permission to create workloads (either Pods, or
[workload resources](/docs/concepts/workloads/controllers/) that manage Pods) in a namespace
implicitly grants access to many other resources in that namespace, such as Secrets, ConfigMaps, and
PersistentVolumes that can be mounted in Pods. Additionally, since Pods can run as any
[ServiceAccount](/docs/reference/access-authn-authz/service-accounts-admin/), granting permission
to create workloads also implicitly grants the API access levels of any service account in that
namespace.  
Users who can run privileged Pods can use that access to gain node access and potentially to
further elevate their privileges. Where you do not fully trust a user or other principal
with the ability to create suitably secure and isolated Pods, you should enforce either the
**Baseline** or **Restricted** Pod Security Standard.
You can use [Pod Security admission](/docs/concepts/security/pod-security-admission/)
or other (third party) mechanisms to implement that enforcement.  
For these reasons, namespaces should be used to separate resources requiring different levels of
trust or tenancy. It is still considered best practice to follow [least privilege](#least-privilege)
principles and assign the minimum set of permissions, but boundaries within a namespace should be
considered weak.
````

## L22

**Sentence:** The add-on both rely on is metrics-server, which collects the resource metrics used by the Horizontal Pod Autoscaler controller (the controller that grows and shrinks workloads) and by the `kubectl top` utility.

**Cited excerpt:**

````text
The resource metrics pipeline provides a limited set of metrics related to
cluster components such as the
[Horizontal Pod Autoscaler](/docs/tasks/run-application/horizontal-pod-autoscale/)
controller, as well as the `kubectl top` utility.
These  metrics are collected by the lightweight, short-term, in-memory
[metrics-server](https://github.com/kubernetes-sigs/metrics-server) and
are exposed via the `metrics.k8s.io` API.  
metrics-server discovers all nodes on the cluster and
queries each node's
[kubelet](/docs/reference/command-line-tools-reference/kubelet/) for CPU and
memory usage. The kubelet acts as a bridge between the Kubernetes master and
the nodes, managing the pods and containers running on a machine. The kubelet
translates each pod into its constituent containers and fetches individual
container usage statistics from the container runtime through the container
runtime interface. If you use a container runtime that uses Linux cgroups and
namespaces to implement containers, and the container runtime does not publish
usage statistics, then the kubelet can look up those statistics directly
(using code from [cAdvisor](https://github.com/google/cadvisor)).
No matter how those statistics arrive, the kubelet then exposes the aggregated pod
resource usage statistics through the metrics-server Resource Metrics API.
This API is served at `/metrics/resource` on the kubelet's authenticated and
read-only ports.
````

## L23

**Sentence:** The node-local-dns container should be restarted because it is managed as part of a DaemonSet, but each time the container fails this causes a brief DNS downtime.

**Cited excerpt:**

````text
The `node-local-dns` Pods use memory for storing cache entries and processing queries.
Since they do not watch Kubernetes objects, the cluster size or the number of Services / EndpointSlices do not directly affect memory usage. Memory usage is influenced by the DNS query pattern.
From [CoreDNS docs](https://github.com/coredns/deployment/blob/master/kubernetes/Scaling_CoreDNS.md),
> The default cache size is 10000 entries, which uses about 30 MB when completely filled.  
This would be the memory usage for each server block (if the cache gets completely filled).
Memory usage can be reduced by specifying smaller cache sizes.  
The number of concurrent queries is linked to the memory demand, because each extra
goroutine used for handling a query requires an amount of memory. You can set an upper limit
using the `max_concurrent` option in the forward plugin.  
If a `node-local-dns` Pod attempts to use more memory than is available (because of total system
resources, or because of a configured
[resource limit](/docs/concepts/configuration/manage-resources-containers/)), the operating system
may shut down that pod's container.
If this happens, the container that is terminated (“OOMKilled”) does not clean up the custom
packet filtering rules that it previously added during startup.
The `node-local-dns` container should get restarted (since managed as part of a DaemonSet), but this
will lead to a brief DNS downtime each time that the container fails: the packet filtering rules direct
DNS queries to a local Pod that is unhealthy.  
You can determine a suitable memory limit by running node-local-dns pods without a limit and
measuring the peak usage. You can also set up and use a
[VerticalPodAutoscaler](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler)
in _recommender mode_, and then check its recommendations.
````

## L24

**Sentence:** Without such defaults, a container with no memory limit would have no upper bound on memory use, could use all of the memory available on the Node, and could invoke the OOM Killer.

**Cited excerpt:**

````text
If you do not specify a memory limit for a Container, one of the following situations applies:  
* The Container has no upper bound on the amount of memory it uses. The Container
could use all of the memory available on the Node where it is running which in turn could invoke the OOM Killer. Further, in case of an OOM Kill, a container with no resource limits will have a greater chance of being killed.  
* The Container is running in a namespace that has a default memory limit, and the
Container is automatically assigned the default limit. Cluster administrators can use a
[LimitRange](/docs/reference/generated/kubernetes-api//#limitrange-v1-core)
to specify a default value for the memory limit.
````

## L25

**Sentence:** `--service-account-max-token-expiration` sets the maximum validity duration of a token created by the service account token issuer, given as a Kubernetes duration string.

**Cited excerpt:**

````text
`--service-account-lookup`
: If true, the API server validates that ServiceAccount tokens exist in etcd as part of authentication.  
`--service-account-max-token-expiration`
: The maximum validity duration of a token created by the service account token issuer, as a Kubernetes duration string.  
`--service-account-signing-endpoint`
: Path to socket where an external JWT signer is listening. You can use this to integrate with an external token signer.  
`--service-account-signing-key-file`
: Path to the file that contains the current private key of the service account token issuer. Changes made to this file while the API server is running are **not** re-read.  
#### Static token configuration {#api-server-authn-config-cli-bearer}  
`--token-auth-file`
: Path to the configuration file for [static bearer tokens](#static-token-file). Changes made to this file while the API server is running are **not** re-read.  
#### Webhook authentication configuration {#api-server-authn-config-cli-webhook}  
`--authentication-token-webhook-cache-ttl`
: How long (as a Kubernetes duration specification) the API server should cache the outcome of HTTP callouts to validate tokens.  
`--authentication-token-webhook-config-file`
: The path to a kubeconfig format client configuration, that specifies how the API server authenticates when making HTTP callouts. Changes made to this file while the API server is running are **not** re-read.  
`--authentication-token-webhook-version`
: The API version of TokenReview to use when making HTTP callouts to check tokens.  
#### Web request authentication configuration {#api-server-authn-config-cli-reverse-proxy}  
Caution:
You should read the documentation about configuring an [authenticating proxy](#authenticating-proxy)
before you specify these command line arguments, as there is important information security advice
that you must follow.  
`--requestheader-client-ca-file`
: _Required._
Path to a PEM-encoded certificate bundle containing trust anchor(s) for validating authenticating proxy identity.
A valid [client certificate](#reverse-proxy-client-certificate)
must be presented and validated against the certificate authorities in the specified file before the
request headers are checked for user names.  
`--requestheader-allowed-names`
: _Optional._ Comma-separated list of Common Name values (CNs).
If set, a valid client
certificate with a CN in the specified list must be presented before the request headers are checked
for user names. If empty, any CN is allowed.  
`--requestheader-username-headers`
: _Required; case-insensitive._ Header names to check, in order, for the user identity.
````

## L26

**Sentence:** Once the `schedulingGates` are removed entirely, the scheduler is informed that the Pod is ready for scheduling, and in the example the Pod moves from `SchedulingGated` to `Running`.

**Cited excerpt:**

````text
To mark a Pod not-ready for scheduling, you can create it with one or more scheduling gates like this:  
```yaml
apiVersion: v1
kind: Pod
metadata:
name: test-pod
spec:
schedulingGates:
- name: example.com/foo
- name: example.com/bar
containers:
- name: pause
image: registry.k8s.io/pause:3.6
```  
After the Pod's creation, you can check its state using:  
```bash
kubectl get pod test-pod
```  
The output reveals it's in `SchedulingGated` state:  
```none
NAME       READY   STATUS            RESTARTS   AGE
test-pod   0/1     SchedulingGated   0          7s
```  
You can also check its `schedulingGates` field by running:  
```bash
kubectl get pod test-pod -o jsonpath='{.spec.schedulingGates}'
```  
The output is:  
```none
[{"name":"example.com/foo"},{"name":"example.com/bar"}]
```  
To inform scheduler this Pod is ready for scheduling, you can remove its `schedulingGates` entirely
by reapplying a modified manifest:  
```yaml
apiVersion: v1
kind: Pod
metadata:
name: test-pod
spec:
containers:
- name: pause
image: registry.k8s.io/pause:3.6
```  
You can check if the `schedulingGates` is cleared by running:  
```bash
kubectl get pod test-pod -o jsonpath='{.spec.schedulingGates}'
```  
The output is expected to be empty. And you can check its latest status by running:  
```bash
kubectl get pod test-pod -o wide
```  
Given the test-pod doesn't request any CPU/memory resources, it's expected that this Pod's state get
transited from previous `SchedulingGated` to `Running`:  
```none
NAME       READY   STATUS    RESTARTS   AGE   IP         NODE
test-pod   1/1     Running   0          15s   10.0.0.4   node-2
```
````

## L27

**Sentence:** When you enable or disable groups or resources, you need to restart the API server and controller manager to pick up the `--runtime-config` changes.

**Cited excerpt:**

````text
Certain resources and API groups are enabled by default. You can enable or
disable them by setting `--runtime-config` on the API server.  The
`--runtime-config` flag accepts comma separated `<key>[=<value>]` pairs
describing the runtime configuration of the API server. If the `=<value>`
part is omitted, it is treated as if `=true` is specified. For example:  
- to disable `batch/v1`, set `--runtime-config=batch/v1=false`
- to enable `batch/v2alpha1`, set `--runtime-config=batch/v2alpha1`
- to enable a specific version of an API, such as `storage.k8s.io/v1beta1/csistoragecapacities`, set `--runtime-config=storage.k8s.io/v1beta1/csistoragecapacities`  
Note:
When you enable or disable groups or resources, you need to restart the API
server and controller manager to pick up the `--runtime-config` changes.
````

## L28

**Sentence:** Another special key, `api/legacy`, represents only legacy APIs, meaning those that have been explicitly deprecated.

**Cited excerpt:**

````text
This page shows how to enable or disable an API version from your cluster's
control plane.  
Specific API versions can be turned on or off by passing `--runtime-config=api/<version>` as a
command line argument to the API server. The values for this argument are a comma-separated
list of API versions. Later values override earlier values.  
The `runtime-config` command line argument also supports 2 special keys:  
- `api/all`, representing all known APIs
- `api/legacy`, representing only legacy APIs. Legacy APIs are any APIs that have been
explicitly [deprecated](/docs/reference/using-api/deprecation-policy/).  
For example, to turn off all API versions except v1, pass `--runtime-config=api/all=false,api/v1=true`
to the `kube-apiserver`.
````

## L29

**Sentence:** Extra permissions and subjects that you added are left in place during that update, so additions you make by hand would survive a restart.

**Cited excerpt:**

````text
Type: Annotation  
Example: `rbac.authorization.kubernetes.io/autoupdate: "false"`  
Used on: ClusterRole, ClusterRoleBinding, Role, RoleBinding  
When this annotation is set to `"true"` on default RBAC objects created by the API server,
they are automatically updated at server start to add missing permissions and subjects
(extra permissions and subjects are left in place).
To prevent autoupdating a particular role or rolebinding, set this annotation to `"false"`.
If you create your own RBAC objects and set this annotation to `"false"`, `kubectl auth reconcile`
(which allows reconciling arbitrary RBAC objects in a manifest)
respects this annotation and does not automatically add missing permissions and subjects.
````

## L30

**Sentence:** Each string in `schedulingGates` is treated as a criterion the Pod must satisfy before it is considered schedulable.

**Cited excerpt:**

````text
Feature state: Kubernetes v1.30 [stable]  
Pods were considered ready for scheduling once created. Kubernetes scheduler
does its due diligence to find nodes to place all pending Pods. However, in a
real-world case, some Pods may stay in a "miss-essential-resources" state for a long period.
These Pods actually churn the scheduler (and downstream integrators like Cluster AutoScaler)
in an unnecessary manner.  
By specifying/removing a Pod's `.spec.schedulingGates`, you can control when a Pod is ready
to be considered for scheduling.

Configuring Pod schedulingGates
The `schedulingGates` field contains a list of strings, and each string literal is perceived as a
criteria that Pod should be satisfied before considered schedulable. This field can be initialized
only when a Pod is created (either by the client, or mutated during admission). After creation,
each schedulingGate can be removed in arbitrary order, but addition of a new scheduling gate is disallowed.  
Figure: Figure. Pod SchedulingGates
````
