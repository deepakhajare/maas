#!/bin/bash

{
mkdir -p /var/lib/cobbler/isos
cd /var/lib/cobbler/isos
archs="i386 amd64"
rels="natty"
mirror="http://archive.ubuntu.com/ubuntu"
for a in $archs; do
   for r in $rels; do
     u=$mirror/dists/$r/main/installer-$a/current/images/netboot/mini.iso
     wget -O $r-$a-mini.iso $u
   done
done

fb_d="/root/first-boot.d"
mkdir -p "$fb_d"
sed -i '/^exit 0/d' /etc/rc.local
cat >> /etc/rc.local <<EOF
## first boot finish stuff
if [ ! -f "$fb_d.done" ]; then
   run-parts "$fb_d" 2>&1 | tee "${fb_d}.log"
   touch "$fb_d.done"
fi
EOF

cat >"$fb_d/10-addl-pkgs" <<"EOF"
#!/bin/sh
pkgs="ubuntu-orchestra-provisioning-server cman"
[ -t 1 ] || {
   unset DEBIAN_HAS_FRONTEND DEBIAN_FRONTEND DEBCONF_REDIR DEBCONF_OLD_FD_BASE;
   export DEBIAN_FRONTEND=noninteractive;
}
if [ "$(lsb_release --codename --short)" = "natty" ]; then
   for p in ppa:orchestra/ppa ppa:dotdee/ppa; do apt-add-repository $p; done
fi
apt-get update
apt-get install --assume-yes ${pkgs}
EOF

cat > "$fb_d/99-halt" <<EOF
#!/bin/sh
touch "$fb_d.done"
/sbin/poweroff
EOF

cat >"$fb_d/50-setup-cobbler" <<"EOF"
#!/bin/sh
mkdir -p /var/lib/cobbler/isos
cd /var/lib/cobbler/isos
[ $# -eq 0 ] && set -- natty:i386 natty:amd64
mirror="${MIRROR:-http://archive.ubuntu.com/ubuntu}"
for t in "$@"; do
   rel=${t%:*}; arch=${t#*:}
   iso=$r-$a-mini.iso
   [ -f "$iso" ] || continue
   u=$mirror/dists/$r/main/installer-$a/current/images/netboot/mini.iso
   wget -O "$iso" "$u"
done

seed="/etc/orchestra/ubuntu-orchestra-client.seed"
for t in "$@"; do
   rel=${t%:*}; arch=${t#*:}
   xa=$arch; [ "$arch" = "amd64" ] && xa=x86_64
   mount -o loop $rel-$arch-mini.iso /mnt 
   cobbler import --name=$rel-$arch --path=/mnt --breed=ubuntu --os-version=$rel --arch=$xa
   umount /mnt
   cobbler profile edit --name $rel-$arch --kickstart=$seed --kopts="priority=critical locale=en_US"
  done 
done
EOF

chmod u+x "$fb_d"/*
} 2>&1 | tee /root/late.log
