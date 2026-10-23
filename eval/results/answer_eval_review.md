# Answer eval: review report

Built from `answer_eval_generation.jsonl` and `answer_eval_verification.jsonl` only. Verdicts come from the Haiku verifier (claims-v2); they are not hand-checked yet (checkpoint 4).

## Outcome vs context coverage (answerable questions, n = 26)

Coverage = at least one expected doc is among the 8 context chunks. A refusal with coverage = no is a retrieval miss; a refusal with coverage = yes is a generation decision.

| config | covered & answered | covered & refused | not covered & answered | not covered & refused |
|---|---|---|---|---|
| heading/hybrid | 20 | 1 | 1 | 4 |
| heading/dense | 22 | 0 | 1 | 3 |

False refusals: heading/hybrid c001 (expected doc NOT in context); heading/hybrid c002 (expected doc NOT in context); heading/hybrid c005 (expected doc in context); heading/hybrid c009 (expected doc NOT in context); heading/hybrid c010 (expected doc NOT in context); heading/dense m008 (expected doc NOT in context); heading/dense c009 (expected doc NOT in context); heading/dense c010 (expected doc NOT in context)

## Unanswerable questions: full answers

### u001 / heading/hybrid: What is the default value of the kube-controller-manager --terminated-pod-gc-threshold flag?

answerable=False; context: deployment, kube-controller-manager-config.v1alpha1, kubelet-config.v1beta1, node-pressure-eviction, pod-lifecycle, scheduler-perf-tuning

> The provided documentation does not cover the default value of the kube-controller-manager --terminated-pod-gc-threshold flag.  (citations [])

### u001 / heading/dense: What is the default value of the kube-controller-manager --terminated-pod-gc-threshold flag?

answerable=False; context: kube-controller-manager-config.v1alpha1, node-pressure-eviction, pod-lifecycle, probes, scheduler-perf-tuning, topology-manager

> The provided documentation does not cover the default value of the kube-controller-manager --terminated-pod-gc-threshold flag.  (citations [])

### u002 / heading/hybrid: What is the default minimum number of conntrack entries that kube-proxy allocates, as set by --conntrack-min?

answerable=False; context: debug-service, kube-proxy-config.v1alpha1, kubelet-in-userns, metrics, virtual-ips

> The provided documentation does not cover the default value of the minimum number of conntrack entries (--conntrack-min) that kube-proxy allocates.  (citations [])

### u002 / heading/dense: What is the default minimum number of conntrack entries that kube-proxy allocates, as set by --conntrack-min?

answerable=False; context: kernel-version-requirements, kube-proxy-config.v1alpha1, kubelet-config.v1beta1, node-pressure-eviction, statefulset, virtual-ips

> The provided documentation does not cover the default value of the minimum number of conntrack entries (--conntrack-min) that kube-proxy allocates.  (citations [])

### u003 / heading/hybrid: How do I bake a loaf of sourdough bread at home?

answerable=False; context: admission-controllers, configure-access-multiple-clusters, coredns, debug-service, kubeadm-certs, parallel-processing-expansion, pull-image-private-registry

> The provided documentation does not cover how to bake a loaf of sourdough bread at home.  (citations [])

### u003 / heading/dense: How do I bake a loaf of sourdough bread at home?

answerable=False; context: certificates, coredns, debug-service, dns-custom-nameservers, dns-pod-service, pull-image-private-registry, static-pod

> The provided documentation does not cover how to bake a loaf of sourdough bread, as it only addresses Kubernetes topics.  (citations [])

### u004 / heading/hybrid: How many moons does Jupiter have?

answerable=False; context: _index, cron-jobs, debug-service, horizontal-pod-autoscale, job, replicationcontroller, storage-limits, topology-manager

> The provided documentation does not cover this question.  (citations [])

### u004 / heading/dense: How many moons does Jupiter have?

answerable=False; context: _index, job, kube-controller-manager-config.v1alpha1, metrics, resource-quotas, storage-limits, topology-manager

> The provided documentation does not cover the question of how many moons Jupiter has.  (citations [])

## Usage and cost (from the `usage` fields)

| step | calls | input tokens | output tokens | cost | per call |
|---|---|---|---|---|---|
| generation | 60 | 296,371 | 11,613 | $0.7089 | 4,940 in / 194 out / $0.0118 |
| verification | 44 | 92,715 | 22,884 | $0.0207 | 2,107 in / 520 out / $0.0005 |

Total $0.7296 for 60 questions x configs ($0.0122 per question-config; 0.0243 per question across both configs). Refusals cost less (about 70 output tokens) than answers.

The run printed a total spend of $0.7295 (spend guard); the logs sum to less because the one failed verification call (hybrid e007) did not record its usage in this run (fixed in rag/verify.py afterwards, see NOTES.md).

- heading/hybrid: generation $0.3689, mean latency 3.3s
- heading/dense: generation $0.3400, mean latency 3.8s

## Verifier output that is not `yes`

Verification errors (no verdicts, excluded from faithfulness): none

11 of 165 cited pairs were not `yes`. Each appears once below with an id. Group A: 7 pairs on 6 sentences whose best verdict is not `yes` (these sentences count as not strictly supported). Group B: 4 pairs whose sentence is still `yes` through another citation.

| id | config | question | sentence | excerpt | verdict | sentence's best verdict | group |
|---|---|---|---|---|---|---|---|
| P01 | heading/dense | c002 | s1 | [5] | PARTIAL | partial | A |
| P02 | heading/dense | c007 | s1 | [3] | PARTIAL | yes | B |
| P03 | heading/dense | c007 | s3 | [4] | PARTIAL | partial | A |
| P04 | heading/dense | m005 | s1 | [1] | PARTIAL | partial | A |
| P05 | heading/hybrid | c003 | s1 | [6] | PARTIAL | partial | A |
| P06 | heading/hybrid | c003 | s3 | [5] | PARTIAL | yes | B |
| P07 | heading/hybrid | c004 | s5 | [1] | PARTIAL | partial | A |
| P08 | heading/hybrid | c004 | s5 | [3] | PARTIAL | partial | A |
| P09 | heading/hybrid | e005 | s1 | [1] | NO | yes | B |
| P10 | heading/hybrid | e006 | s5 | [6] | PARTIAL | yes | B |
| P11 | heading/hybrid | m008 | s3 | [4] | PARTIAL | partial | A |

### P01: heading/dense c002 sentence 1 vs excerpt [5]: **PARTIAL** (sentence's best verdict: partial; group A)

Sentence: The add-on both rely on is metrics-server, which collects the resource metrics used by the Horizontal Pod Autoscaler controller (the controller that grows and shrinks workloads) and by the `kubectl top` utility.

Verifier reason: Excerpt confirms metrics-server supplies metrics to HPA and kubectl top, but does not describe HPA as growing/shrinking workloads or say 'add-on both rely on'.

Claims: supported: metrics-server collects the resource metrics used by the Horizontal Pod Autoscaler controller and by kubectl top., unsupported: The Horizontal Pod Autoscaler controller is described as the controller that grows and shrinks workloads., unsupported: The add-on both rely on is metrics-server.

Excerpt [5] (tasks/debug/debug-cluster/resource-usage-monitoring | Tools for Monitoring Resources > Resource metrics pipeline; expected doc: True):

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

### P02: heading/dense c007 sentence 1 vs excerpt [3]: **PARTIAL** (sentence's best verdict: yes; group B)

Sentence: When a container is created without a memory request or limit in a namespace that has a LimitRange, the cluster applies the default memory request and limit from that LimitRange to the container.

Verifier reason: Excerpt says the control plane applies a default memory limit to containers without one; it does not mention a default request.

Claims: supported: When a container is created without a memory request or limit in a namespace with a LimitRange, the cluster applies the default memory request and limit from that LimitRange., unsupported: The default applied is a memory limit only; no default memory request is mentioned.

Excerpt [3] (tasks/administer-cluster/manage-resources/memory-default-namespace | Configure Default Memory Requests and Limits for a Namespace > Motivation for default memory limits and requests; expected doc: True):

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

### P03: heading/dense c007 sentence 3 vs excerpt [4]: **PARTIAL** (sentence's best verdict: partial; group A)

Sentence: Without such defaults, a container with no memory limit would have no upper bound on memory use, could use all of the memory available on the Node, and could invoke the OOM Killer.

Verifier reason: Excerpt states a container with no memory limit may use all Node memory and invoke the OOM Killer, but the 'without such defaults' framing is an extrapolation.

Claims: supported: Without a memory limit, a container has no upper bound on memory use and could use all memory available on the Node., supported: Such a container could invoke the OOM Killer., unsupported: The absence of defaults is the condition under which this happens.

Excerpt [4] (tasks/configure-pod-container/assign-memory-resource | Assign Memory Resources to Containers and Pods > If you do not specify a memory limit; expected doc: False):

````text
If you do not specify a memory limit for a Container, one of the following situations applies:  
* The Container has no upper bound on the amount of memory it uses. The Container
could use all of the memory available on the Node where it is running which in turn could invoke the OOM Killer. Further, in case of an OOM Kill, a container with no resource limits will have a greater chance of being killed.  
* The Container is running in a namespace that has a default memory limit, and the
Container is automatically assigned the default limit. Cluster administrators can use a
[LimitRange](/docs/reference/generated/kubernetes-api//#limitrange-v1-core)
to specify a default value for the memory limit.
````

### P04: heading/dense m005 sentence 1 vs excerpt [1]: **PARTIAL** (sentence's best verdict: partial; group A)

Sentence: No, they do not matter: the scheduler only considers nodes that have all of the topologySpreadConstraints[*].topologyKey labels present at the same time, and nodes missing any of them are bypassed.

Verifier reason: Excerpt states nodes missing any topologyKey are bypassed; the 'No, they do not matter' framing answers a question not present in the excerpt.

Claims: supported: The scheduler only considers nodes that have all of the topologySpreadConstraints[*].topologyKey labels present at the same time., supported: Nodes missing any of them are bypassed., unsupported: The question of whether certain nodes matter is answered 'No, they do not matter'.

Excerpt [1] (concepts/scheduling-eviction/topology-spread-constraints | Pod Topology Spread Constraints > Implicit conventions; expected doc: True):

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

### P05: heading/hybrid c003 sentence 1 vs excerpt [6]: **PARTIAL** (sentence's best verdict: partial; group A)

Sentence: The newer approach is Server-Side Apply, which is meant as a replacement for the original client-side implementation of `kubectl apply`.

Verifier reason: Excerpt 6 states Server-Side Apply is meant as a replacement for the original client-side kubectl apply; 'newer' is not stated but is minor framing.

Claims: unsupported: Server-Side Apply is the newer approach., supported: Server-Side Apply is meant as a replacement for the original client-side implementation of kubectl apply.

Excerpt [6] (reference/using-api/server-side-apply | Server-Side Apply > Comparison with Client-Side Apply; expected doc: True):

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

### P06: heading/hybrid c003 sentence 3 vs excerpt [5]: **PARTIAL** (sentence's best verdict: yes; group B)

Sentence: Rather than tracking a user's last applied state as the legacy `last-applied` annotation does, Server-Side Apply tracks an object's field management, so information about which field manager manages each field becomes available.

Verifier reason: Excerpt 5 contrasts the approaches only briefly and does not state that field manager information becomes available as a result.

Claims: supported: Server-Side Apply tracks an object's field management rather than the user's last applied state., unsupported: Information about which field manager manages each field becomes available.

Excerpt [5] (reference/using-api/server-side-apply | Server-Side Apply > Field management; expected doc: True):

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

### P07: heading/hybrid c004 sentence 5 vs excerpt [1]: **PARTIAL** (sentence's best verdict: partial; group A)

Sentence: Users who can run privileged Pods can use that access to gain node access and potentially elevate their privileges further, and any containers running with privileged: true on a node can access all Secrets used on that node.

Verifier reason: Warning states privileged: true containers on a node can access all Secrets used on that node; privileged Pod escalation is not mentioned.

Claims: unsupported: Users who can run privileged Pods can gain node access and potentially elevate privileges further., supported: Containers running with privileged: true on a node can access all Secrets used on that node.

Excerpt [1] (concepts/configuration/secret | Secrets > Information security for Secrets; expected doc: False):

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

### P08: heading/hybrid c004 sentence 5 vs excerpt [3]: **PARTIAL** (sentence's best verdict: partial; group A)

Sentence: Users who can run privileged Pods can use that access to gain node access and potentially elevate their privileges further, and any containers running with privileged: true on a node can access all Secrets used on that node.

Verifier reason: Excerpt 3 covers privileged Pods gaining node access but not the Secrets claim, which is in excerpt 1.

Claims: supported: Users who can run privileged Pods can gain node access and potentially elevate privileges further., unsupported: Containers running with privileged: true on a node can access all Secrets used on that node.

Excerpt [3] (concepts/security/rbac-good-practices | Role Based Access Control Good Practices > Kubernetes RBAC - privilege escalation risks {#privilege-escalation-risks} > Workload creation; expected doc: False):

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

### P09: heading/hybrid e005 sentence 1 vs excerpt [1]: **NO** (sentence's best verdict: yes; group B)

Sentence: preBind plugins perform any work required before a Pod is bound.

Verifier reason: Excerpt 1 lists the preBind extension point only by name and does not describe its purpose; the description appears in excerpt 4.

Claims: unsupported: preBind plugins perform any work required before a Pod is bound.

Excerpt [1] (reference/scheduling/config | Scheduler Configuration > Profiles > Extension points; expected doc: True):

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

### P10: heading/hybrid e006 sentence 5 vs excerpt [6]: **PARTIAL** (sentence's best verdict: yes; group B)

Sentence: Controllers copy the schedulingPolicy from the template into each CompositePodGroup they create, and minGroupCount in a CompositePodGroupTemplate is immutable.

Verifier reason: Excerpt says the policy is copied from the template at creation, but says nothing about minGroupCount immutability.

Claims: supported: Controllers copy the schedulingPolicy from the template into each CompositePodGroup they create., unsupported: minGroupCount in a CompositePodGroupTemplate is immutable.

Excerpt [6] (concepts/workloads/compositepodgroup-api/_index | CompositePodGroup API > API structure > Scheduling policy; expected doc: False):

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

### P11: heading/hybrid m008 sentence 3 vs excerpt [4]: **PARTIAL** (sentence's best verdict: partial; group A)

Sentence: Those packet filtering rules direct DNS queries to a local Pod that is now unhealthy, so lookups fail.

Verifier reason: Excerpt says rules direct queries to an unhealthy Pod but does not explicitly state that lookups fail.

Claims: supported: The packet filtering rules direct DNS queries to a local Pod that is now unhealthy., unsupported: Lookups fail as a result.

Excerpt [4] (tasks/administer-cluster/nodelocaldns | Using NodeLocal DNSCache in Kubernetes Clusters > Setting memory limits; expected doc: True):

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
