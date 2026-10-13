function code --wraps=code-oss --description 'Route Code OSS profile: Default lite, .NET only for Dotnet study'
    set -l DOTNET_ROOT "/run/media/narol/HDD/repos/VS2022_repos/study/Dotnet_Backend_non_CP_study"
    set -l NET_PROFILE "C# .NET"
    set -l LITE_PROFILE "Default"

    # Explicit profile always wins
    if contains -- --profile $argv
        if set -q CODE_ROUTER_DRY_RUN
            echo "PASSTHROUGH: code-oss $argv"
            return 0
        end
        command code-oss $argv
        return $status
    end

    # Flag-only operations passthrough without injecting a profile
    for f in $argv
        switch $f
            case --help -h --version -v --list-extensions --status -s
                if set -q CODE_ROUTER_DRY_RUN
                    echo "PASSTHROUGH: code-oss $argv"
                    return 0
                end
                command code-oss $argv
                return $status
        end
    end

    # Collect path args; fall back to CWD (covers `code .` and bare `code`)
    set -l targets
    for a in $argv
        if not string match -q -- '-*' $a
            set -a targets $a
        end
    end
    if test (count $targets) -eq 0
        set targets $PWD
    end

    set -l want_net 0
    for t in $targets
        set -l resolved (realpath -m -- "$t" 2>/dev/null; or echo "$t")

        # 1. Under DOTNET_ROOT (exact or child)
        if test "$resolved" = "$DOTNET_ROOT"
            set want_net 1
            break
        end
        if string match -q -- "$DOTNET_ROOT/*" "$resolved"
            set want_net 1
            break
        end

        # 2. C# project file argument
        if string match -q -- '*.sln' "$resolved"; or string match -q -- '*.slnx' "$resolved"; or string match -q -- '*.csproj' "$resolved"; or string match -q -- '*.cs' "$resolved"
            set want_net 1
            break
        end

        # 3. Directory containing a solution/project (maxdepth 2, cheap)
        if test -d "$resolved"
            set -l hit (find "$resolved" -maxdepth 2 \( -name '*.sln' -o -name '*.csproj' \) -print -quit 2>/dev/null)
            if test -n "$hit"
                set want_net 1
                break
            end
        end
    end

    if test $want_net -eq 1
        if set -q CODE_ROUTER_DRY_RUN
            echo "PROFILE=$NET_PROFILE $argv"
            return 0
        end
        command code-oss --profile "$NET_PROFILE" $argv
    else
        if set -q CODE_ROUTER_DRY_RUN
            echo "PROFILE=$LITE_PROFILE $argv"
            return 0
        end
        command code-oss --profile "$LITE_PROFILE" $argv
    end
end
