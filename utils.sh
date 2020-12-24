
if [ $(uname) = Darwin ]; then
    function getip() {
        ping -c1 $1 | head -1 | sed -e's/.*(\(.*\)).*/\1/'
    }
fi