-- Step builder and utility functions for Buildkite pipeline
let Types = ./types.dhall

let List/map =
      https://prelude.dhall-lang.org/v11.1.0/List/map
        sha256:dd845ffb4568d40327f2a817eb42d1c6138b929ca758d50bc33112ef3c885680

let List/filter =
      https://prelude.dhall-lang.org/v20.1.0/List/filter.dhall
        sha256:8ebfede5bbfe09675f246c33eb83964880ac615c4b1be8d856076fdbc4b26ba6

let Natural/equal =
      https://prelude.dhall-lang.org/v20.1.0/Natural/equal.dhall
        sha256:7f108edfa35ddc7cebafb24dc073478e93a802e13b5bc3fd22f4768c9b066e60

let dockerDindSidecar
    : Types.Container
    = { image = "docker:20.10.16-dind"
      , command = Some [ "dockerd-entrypoint.sh" ]
      , resources = Some { requests.cpu = "500m" }
      , env = Some [ { name = "DOCKER_TLS_CERTDIR", value = "" } ]
      , envFrom = None (List Types.SecretEnvSource)
      , volumeMounts = Some [ { mountPath = "/var/run", name = "docker-sock" } ]
      , securityContext = Some
        { privileged = True, allowPrivilegeEscalation = Some True }
      }

let dockerVolume
    : Types.Volume
    = { name = "docker-sock", emptyDir = {=} }

let dockerVolumeMount
    : Types.VolumeMount
    = { mountPath = "/var/run/", name = "docker-sock" }

let createStep
    : Text ->
      List Text ->
      Text ->
      Optional Types.SecurityContext ->
      Types.BuildCondition ->
      List Types.CachePluginConfig ->
      Bool ->
      List Types.EnvSource ->
        Types.Step
    = \(label : Text) ->
      \(commands : List Text) ->
      \(image : Text) ->
      \(securityContext : Optional Types.SecurityContext) ->
      \(buildCondition : Types.BuildCondition) ->
      \(caches : List Types.CachePluginConfig) ->
      \(withDockerSidecar : Bool) ->
      \(containerEnv : List Types.EnvSource) ->
        let volumeMounts =
              if    withDockerSidecar
              then  Some [ dockerVolumeMount ]
              else  None (List Types.VolumeMount)

        let Optional/toList =
              https://prelude.dhall-lang.org/v20.1.0/Optional/toList.dhall
                sha256:d78f160c619119ef12389e48a629ce293d69f7624c8d016b7a4767ab400344c4

        let List/concatMap =
              https://prelude.dhall-lang.org/v20.1.0/List/concatMap.dhall
                sha256:3b2167061d11fda1e4f6de0522cbe83e0d5ac4ef5ddf6bb0b2064470c5d3fb64

        let envVarsOptional =
              List/map
                Types.EnvSource
                (Optional Types.EnvVar)
                ( \(source : Types.EnvSource) ->
                    merge
                      { EnvVar = \(ev : Types.EnvVar) -> Some ev
                      , SecretEnvSource =
                          \(ses : Types.SecretEnvSource) -> None Types.EnvVar
                      }
                      source
                )
                containerEnv

        let secretEnvSourcesOptional =
              List/map
                Types.EnvSource
                (Optional Types.SecretEnvSource)
                ( \(source : Types.EnvSource) ->
                    merge
                      { EnvVar =
                          \(ev : Types.EnvVar) -> None Types.SecretEnvSource
                      , SecretEnvSource =
                          \(ses : Types.SecretEnvSource) -> Some ses
                      }
                      source
                )
                containerEnv

        let envVars =
              List/concatMap
                (Optional Types.EnvVar)
                Types.EnvVar
                ( \(opt : Optional Types.EnvVar) ->
                    Optional/toList Types.EnvVar opt
                )
                envVarsOptional

        let secretEnvSources =
              List/concatMap
                (Optional Types.SecretEnvSource)
                Types.SecretEnvSource
                ( \(opt : Optional Types.SecretEnvSource) ->
                    Optional/toList Types.SecretEnvSource opt
                )
                secretEnvSourcesOptional

        let hasEnvVars = Natural/equal 0 (List/length Types.EnvVar envVars)

        let hasSecrets =
              Natural/equal
                0
                (List/length Types.SecretEnvSource secretEnvSources)

        let mainContainerEnv =
              if hasEnvVars then None (List Types.EnvVar) else Some envVars

        let mainContainerEnvFrom =
              if    hasSecrets
              then  None (List Types.SecretEnvSource)
              else  Some secretEnvSources

        let mainContainer =
              { image
              , securityContext
              , volumeMounts
              , command = None (List Text)
              , env = mainContainerEnv
              , envFrom = mainContainerEnvFrom
              , resources = None Types.Resources
              }

        let sidecars =
              if    withDockerSidecar
              then  Some [ dockerDindSidecar ]
              else  None (List Types.Container)

        let volumes =
              if    withDockerSidecar
              then  Some [ dockerVolume ]
              else  None (List Types.Volume)

        let kubernetesPlugin =
              Types.Plugin.Kubernetes
                { kubernetes =
                  { gitEnvFrom = [ { secretRef.name = "git-ssh-credentials" } ]
                  , mirrorVolumeMounts = True
                  , podSpec =
                    { containers = [ mainContainer ]
                    , serviceAccountName = "buildkite-job"
                    , volumes
                    }
                  , sidecars
                  }
                }

        let cachePlugins =
              List/map
                Types.CachePluginConfig
                Types.Plugin
                ( \(c : Types.CachePluginConfig) ->
                    Types.Plugin.Cache { `cache#v1.7.0` = c }
                )
                caches

        let allPlugins = [ kubernetesPlugin ] # cachePlugins

        let Text/concatMapSep =
              https://prelude.dhall-lang.org/v20.1.0/Text/concatMapSep.dhall
                sha256:c272aca80a607bc5963d1fcb38819e7e0d3e72ac4d02b1183b1afb6a91340840

        let conditionalFields =
              merge
                { FileChanged =
                    \(filePath : Text) ->
                      { if_changed = Some filePath, `if` = None Text }
                , Branch =
                    \(branches : List Text) ->
                      { if_changed = None Text
                      , `if` = Some
                          ( Text/concatMapSep
                              " || "
                              Text
                              ( \(branch : Text) ->
                                  "build.branch == '${branch}'"
                              )
                              branches
                          )
                      }
                , None = { if_changed = None Text, `if` = None Text }
                }
                buildCondition

        in  { key = label
            , agents.queue = "compass"
            , commands
            , label
            , plugins = allPlugins
            , if_changed = conditionalFields.if_changed
            , `if` = conditionalFields.`if`
            , depends_on = None (List Text)
            }

let buildImageStep
    : Text ->
      Text ->
      Text ->
      Text ->
      Text ->
      Optional Text ->
      Types.BuildCondition ->
        Types.Step
    = \(region : Text) ->
      \(accountId : Text) ->
      \(imageBuilderTag : Text) ->
      \(repoName : Text) ->
      \(dockerfilePath : Text) ->
      \(tagPrefix : Optional Text) ->
      \(condition : Types.BuildCondition) ->
        let tag =
              merge
                { None = "\$BUILDKITE_BUILD_NUMBER"
                , Some =
                    \(prefix : Text) -> "${prefix}.\$BUILDKITE_BUILD_NUMBER"
                }
                tagPrefix

        in  createStep
              "build-${repoName}"
              [ "aws ecr get-login-password --region ${region} | buildah login --username AWS --password-stdin ${accountId}.dkr.ecr.${region}.amazonaws.com"
              , ''
                buildah --storage-driver vfs build \
                  --layers \
                  -f ${dockerfilePath} \
                  --cache-from ${accountId}.dkr.ecr.${region}.amazonaws.com/${repoName} \
                  --cache-to ${accountId}.dkr.ecr.${region}.amazonaws.com/${repoName} \
                  -t ${accountId}.dkr.ecr.${region}.amazonaws.com/${repoName}:${tag} \
                  .
                ''
              , "buildah --storage-driver vfs push ${accountId}.dkr.ecr.${region}.amazonaws.com/${repoName}:${tag}"
              ]
              "${accountId}.dkr.ecr.${region}.amazonaws.com/compass-buildkite-image-builder:${imageBuilderTag}"
              (Some { privileged = True, allowPrivilegeEscalation = None Bool })
              condition
              ([] : List Types.CachePluginConfig)
              False
              ([] : List Types.EnvSource)

let retagImage
    : Text ->
      Text ->
      Text ->
      Text ->
      Text ->
      Text ->
      List Text ->
      Types.BuildCondition ->
        Types.Step
    = \(label : Text) ->
      \(region : Text) ->
      \(accountId : Text) ->
      \(imageBuilderTag : Text) ->
      \(repoName : Text) ->
      \(baseTag : Text) ->
      \(newTags : List Text) ->
      \(buildCondition : Types.BuildCondition) ->
        let manifestCommand =
              "MANIFEST=\$(aws ecr batch-get-image --registry-id ${accountId} --region ${region} --repository-name ${repoName} --image-ids imageTag=${baseTag} --output text --query 'images[].imageManifest')"

        let retagCommands =
              List/map
                Text
                Text
                ( \(newTag : Text) ->
                    "aws ecr put-image --registry-id ${accountId} --repository-name ${repoName} --region ${region} --image-tag ${newTag} --image-manifest \\\$MANIFEST"
                )
                newTags

        let webhookCommand =
              ''
              if [ -n "\$WEBHOOK_ENDPOINT" ] && [ -n "\$WEBHOOK_SIGNATURE" ] && [ -n "\$WEBHOOK_PAYLOAD" ]; then
                echo "Sending webhook notification..."
                curl -d "\$WEBHOOK_PAYLOAD" -X POST -H "X-Signature: sha1=\$WEBHOOK_SIGNATURE" "\$WEBHOOK_ENDPOINT"
              fi
              ''

        let allCommands =
              [ manifestCommand ] # retagCommands # [ webhookCommand ]

        in  createStep
              label
              allCommands
              "${accountId}.dkr.ecr.${region}.amazonaws.com/compass-buildkite-image-builder:${imageBuilderTag}"
              (None Types.SecurityContext)
              buildCondition
              ([] : List Types.CachePluginConfig)
              False
              [ Types.EnvSource.SecretEnvSource
                  { secretRef.name = "webhook-secrets" }
              ]

in  { createStep
    , buildImageStep
    , retagImage
    , dockerDindSidecar
    , dockerVolume
    , dockerVolumeMount
    }
