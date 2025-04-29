{ pkgs ? import <nixpkgs> {} }:
let
  python' = pkgs.python3.withPackages (p: with p; [
    playwright
    beautifulsoup4
    datasets
  ]);
in
  pkgs.mkShell {
    nativeBuildInputs = with pkgs; [
      playwright-driver.browsers
    ];
    packages = [
      python'
    ];

    shellHook = ''
      export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
      export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
    '';
}
