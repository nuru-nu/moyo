
if [ $(uname) = Darwin ]; then
    function getip() {
        ping -c1 $1 | head -1 | sed -e's/.*(\(.*\)).*/\1/'
    }
fi

if [ $(uname -n) = sanduku ]; then
    function getip() {
        avahi-resolve-host-name -4 $1 | awk '{print $2}'
    }
fi
