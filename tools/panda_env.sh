# Source this in every new terminal of the Panda notebook, from the repository folder:
#     source tools/panda_env.sh
# It keeps Claude Code, its login and git settings on /work (the notebook's home directory is wiped
# on every restart), and puts the claude command on PATH.
_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_me="$(dirname "$_repo")"                 # your own folder, e.g. /work/hpham
case "$_me" in
  /work/*) ;;
  *) echo "panda_env.sh: the repository should be inside your folder under /work (now: $_repo)"; return 1 ;;
esac
export HOME="$_me/.home"
mkdir -p "$HOME"
chmod 700 "$HOME" 2>/dev/null
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1
# a GitHub token typed at a git prompt is kept in memory for 8 hours, never written to disk
git config --global credential.helper "cache --timeout=28800"
cd "$_repo"
echo "HOME=$HOME; repository: $_repo; claude: $(command -v claude || echo 'not installed yet')"
unset _repo _me
