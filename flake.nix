{
    description = "Timekeeper - Night pull from iLAB";
    inputs = {
        nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
        flake-utils.url = "github:numtide/flake-utils";
    };

    outputs = {self, nixpkgs, flake-utils}:
        flake-utils.lib.eachDefaultSystem (system:
            let
                pkgs = import nixpkgs {
                    inherit system;
                    config.allowUnfree = true;
                };

                
                system_deps = builtins.attrValues {
                    inherit (pkgs)
                        git
                        uv;
                };
                
                python_base = pkgs.python313;

            in {
                
                devShells.default = pkgs.mkShell {
                    buildInputs = system_deps ++ [ python_base ];

                    shellHook = ''
                        echo "====> Timekeeper - Preparing DEV SHELL <===="

                        export UV_PYTHON="${python_base}/bin/python3"
                        export VIRTUAL_ENV=".venv"

                        if [ ! -d ".venv" ]; then
                            echo "====> Creating uv venv <===="
                            uv venv .venv --python "${python_base}/bin/python3"
                        fi

                        source .venv/bin/activate

                        if [ -f "pyproject.toml" ]; then
                            echo "====> Syncing deps (incl. dev tooling) <===="
                            uv sync
                        fi
                    '';
                };
            }
        );
}