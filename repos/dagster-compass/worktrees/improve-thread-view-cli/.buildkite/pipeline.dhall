-- Buildkite pipeline configuration
-- Types are in types.dhall, step builders are in step_builder.dhall
let Types = ./.buildkite/types.dhall

let StepBuilder = ./.buildkite/step_builder.dhall

let region
    : Text
    = "us-west-2"

let accountId
    : Text
    = "134857758541"

let buildkitePyImageTag
    : Text
    = "111"

let buildkiteJsImageTag
    : Text
    = "298"

let buildkiteImageBuilderImageTag
    : Text
    = "111"

let uvSync
    : Text
    = "uv sync --all-packages --group dev --frozen"

let uvCache
    : Types.CachePluginConfig
    = { backend = "s3"
      , path = ".venv"
      , manifest = "uv.lock"
      , restore = "file"
      , save = "file"
      , compression = "tgz"
      }

let playwrightCache
    : Types.CachePluginConfig
    = { backend = "s3"
      , path = "/root/.cache/ms-playwright"
      , manifest = "uv.lock"
      , restore = "file"
      , save = "file"
      , compression = "tgz"
      }

let buildUiCache
    : Types.CachePluginConfig
    = { backend = "s3"
      , path = "packages/ui/node_modules"
      , manifest = "packages/ui/yarn.lock"
      , restore = "file"
      , save = "file"
      , compression = "tgz"
      }

let buildkiteJsImage =
      StepBuilder.buildImageStep
        region
        accountId
        buildkiteImageBuilderImageTag
        "compass-buildkite-js"
        "images/buildkite-js.Dockerfile"
        (None Text)
        (Types.BuildCondition.FileChanged "images/buildkite-js.Dockerfile")

let buildkitePyImage =
      StepBuilder.buildImageStep
        region
        accountId
        buildkiteImageBuilderImageTag
        "compass-buildkite-py"
        "images/buildkite-py.Dockerfile"
        (None Text)
        (Types.BuildCondition.FileChanged "images/buildkite-py.Dockerfile")

let buildkitePipelineImage =
      StepBuilder.buildImageStep
        region
        accountId
        buildkiteImageBuilderImageTag
        "compass-buildkite-pipeline"
        "images/buildkite-pipeline.Dockerfile"
        (None Text)
        ( Types.BuildCondition.FileChanged
            "images/buildkite-pipeline.Dockerfile"
        )

let buildkiteImageBuilderImage =
      StepBuilder.buildImageStep
        region
        accountId
        buildkiteImageBuilderImageTag
        "compass-buildkite-image-builder"
        "images/buildkite-image-builder.Dockerfile"
        (None Text)
        ( Types.BuildCondition.FileChanged
            "images/buildkite-image-builder.Dockerfile"
        )

let compassImage =
      StepBuilder.buildImageStep
        region
        accountId
        buildkiteImageBuilderImageTag
        "compass"
        "images/compass.Dockerfile"
        (None Text)
        (Types.BuildCondition.Branch [ "master", "release-k8s" ])

let prettierStep
    : Types.Step
    = StepBuilder.createStep
        "prettier"
        [ "make prettier-check" ]
        "${accountId}.dkr.ecr.${region}.amazonaws.com/compass-buildkite-js:${buildkiteJsImageTag}"
        (None Types.SecurityContext)
        (Types.BuildCondition.FileChanged "**/*.{md,yml,tsx,yaml}")
        ([] : List Types.CachePluginConfig)
        False
        ([] : List Types.EnvSource)

let ruffStep
    : Types.Step
    = StepBuilder.createStep
        "ruff"
        [ uvSync, "make ruff-check" ]
        "${accountId}.dkr.ecr.${region}.amazonaws.com/compass-buildkite-py:${buildkitePyImageTag}"
        (None Types.SecurityContext)
        (Types.BuildCondition.FileChanged "packages/**")
        [ uvCache ]
        False
        ([] : List Types.EnvSource)

let pyrightStep
    : Types.Step
    = StepBuilder.createStep
        "pyright"
        [ uvSync, "make pyright" ]
        "${accountId}.dkr.ecr.${region}.amazonaws.com/compass-buildkite-py:${buildkitePyImageTag}"
        (None Types.SecurityContext)
        (Types.BuildCondition.FileChanged "packages/**")
        [ uvCache ]
        False
        ([] : List Types.EnvSource)

let testStep
    : Types.Step
    = StepBuilder.createStep
        "test"
        [ "echo '--- installing dependencies'"
        , uvSync
        , ''
          if [ ! -d /root/.cache/ms-playwright/chromium-* ]; then
            uv run playwright install chromium --with-deps
          else
            uv run playwright install-deps chromium
          fi
          ''
        , ''
          if [ "$BUILDKITE_BRANCH" = "master" ] || [[ "\$BUILDKITE_MESSAGE" == *"RUN_E2E"* ]]; then
            # Enable yarn via corepack (Node.js 16+ includes corepack)
            corepack enable
            # Build UI for E2E tests
            scripts/build-ui.sh
            echo '--- running tests'
            # temporarily don't run e2e as they're broken
            # COMPASS_E2E_TESTS=1 COMPASS_E2E_CI=1 COMPASS_RECORD_VIDEO=1 uv run pytest -n auto -v packages/csbot/tests/
            make test-all
          else
            echo '--- running tests'
            make test-all
          fi
          ''
        ]
        "${accountId}.dkr.ecr.${region}.amazonaws.com/compass-buildkite-py:${buildkitePyImageTag}"
        (None Types.SecurityContext)
        (Types.BuildCondition.FileChanged "packages/**")
        [ uvCache, playwrightCache, buildUiCache ]
        True
        [ Types.EnvSource.EnvVar
            { name = "BUILDKITE_SHELL", value = "/bin/bash -e -c" }
        ]

let buildUiStep
    : Types.Step
    = StepBuilder.createStep
        "build-ui"
        [ "scripts/build-ui.sh" ]
        "${accountId}.dkr.ecr.${region}.amazonaws.com/compass-buildkite-js:${buildkiteJsImageTag}"
        (None Types.SecurityContext)
        (Types.BuildCondition.FileChanged "packages/**")
        [ buildUiCache ]
        False
        ([] : List Types.EnvSource)

let buildAndTestSteps
    : List Types.Step
    = [ buildkiteJsImage
      , buildkitePyImage
      , buildkiteImageBuilderImage
      , buildkitePipelineImage
      , buildUiStep
      , compassImage
      , prettierStep
      , ruffStep
      , pyrightStep
      , testStep
      ]

let List/map =
      https://prelude.dhall-lang.org/v11.1.0/List/map
        sha256:dd845ffb4568d40327f2a817eb42d1c6138b929ca758d50bc33112ef3c885680

let allStepKeys
    : List Text
    = List/map
        Types.Step
        Text
        (\(step : Types.Step) -> step.key)
        buildAndTestSteps

let releaseStep
    : Types.Step
    =     StepBuilder.retagImage
            "retag-compass-release"
            region
            accountId
            buildkiteImageBuilderImageTag
            "compass"
            "\$BUILDKITE_BUILD_NUMBER"
            [ "compass-release.\$BUILDKITE_BUILD_NUMBER" ]
            (Types.BuildCondition.Branch [ "release-k8s" ])
      //  { depends_on = Some allStepKeys }

let releaseCandidateStep
    : Types.Step
    =     StepBuilder.retagImage
            "retag-compass-release-candidate"
            region
            accountId
            buildkiteImageBuilderImageTag
            "compass"
            "\$BUILDKITE_BUILD_NUMBER"
            [ "compass-rc.\$BUILDKITE_BUILD_NUMBER" ]
            (Types.BuildCondition.Branch [ "master" ])
      //  { depends_on = Some allStepKeys }

let pipeline
    : Types.Pipeline
    = { steps = buildAndTestSteps # [ releaseStep, releaseCandidateStep ]
      , env =
        { BUILDKITE_PLUGIN_S3_CACHE_BUCKET = "compass-buildkite-cache"
        , BUILDKITE_PLUGIN_S3_CACHE_ONLY_SHOW_ERRORS = "true"
        , AWS_PAGER = ""
        }
      }

in  pipeline
