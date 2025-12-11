-- Type definitions for Buildkite pipeline

let SecurityContext =
      { privileged : Bool, allowPrivilegeEscalation : Optional Bool }

let SecretRef = { name : Text }

let EnvVar = { name : Text, value : Text }

let SecretEnvSource = { secretRef : SecretRef }

let EnvSource = < EnvVar : EnvVar | SecretEnvSource : SecretEnvSource >

let VolumeMount = { mountPath : Text, name : Text }

let ResourceRequests = { cpu : Text }

let Resources = { requests : ResourceRequests }

let Container =
      { image : Text
      , securityContext : Optional SecurityContext
      , volumeMounts : Optional (List VolumeMount)
      , command : Optional (List Text)
      , env : Optional (List EnvVar)
      , envFrom : Optional (List SecretEnvSource)
      , resources : Optional Resources
      }

let EmptyDir = {}

let Volume = { name : Text, emptyDir : EmptyDir }

let PodSpec =
      { containers : List Container
      , serviceAccountName : Text
      , volumes : Optional (List Volume)
      }

let GitEnvFrom = { secretRef : SecretRef }

let KubernetesPlugin =
      { gitEnvFrom : List GitEnvFrom
      , mirrorVolumeMounts : Bool
      , podSpec : PodSpec
      , sidecars : Optional (List Container)
      }

let CachePluginConfig =
      { backend : Text
      , path : Text
      , manifest : Text
      , restore : Text
      , save : Text
      , compression : Text
      }

let KubernetesPluginWrapper = { kubernetes : KubernetesPlugin }

let CachePluginWrapper = { `cache#v1.7.0` : CachePluginConfig }

let Plugin =
      < Kubernetes : KubernetesPluginWrapper | Cache : CachePluginWrapper >

let Plugins = List Plugin

let Agents = { queue : Text }

let BuildCondition = < FileChanged : Text | Branch : List Text | None >

let Step =
      { key : Text
      , agents : Agents
      , commands : List Text
      , label : Text
      , plugins : Plugins
      , if_changed : Optional Text
      , `if` : Optional Text
      , depends_on : Optional (List Text)
      }

let Env =
      { BUILDKITE_PLUGIN_S3_CACHE_BUCKET : Text
      , BUILDKITE_PLUGIN_S3_CACHE_ONLY_SHOW_ERRORS : Text
      , AWS_PAGER : Text
      }

let Pipeline = { steps : List Step, env : Env }

in  { SecurityContext
    , EnvVar
    , SecretEnvSource
    , EnvSource
    , VolumeMount
    , ResourceRequests
    , Resources
    , Container
    , EmptyDir
    , Volume
    , SecretRef
    , PodSpec
    , GitEnvFrom
    , KubernetesPlugin
    , CachePluginConfig
    , KubernetesPluginWrapper
    , CachePluginWrapper
    , Plugin
    , Plugins
    , Agents
    , BuildCondition
    , Step
    , Env
    , Pipeline
    }
