git clone https://github.com/feederbox826/FansDB-SHALookup.git
rm -Rf FansDB-SHALookup/.git FansDDB-SHALookup/.gitignore
mv FansDB-SHALookup/config.py{.example,}
zip -9 -r -j FansDB-SHALookup.zip FansDB-SHALookup/
DATE=`date +"%Y-%m-%d %H:%M:%S %z"`
SHA256=`sha256sum FansDB-SHALookup.zip | awk '{print $1}'`
VERSION=`grep "VERSION =" FansDB-SHALookup/SHALookup.py | awk '{print $3}' | tr -d '"'`
cat << EOF > index.yml
- id: FansDB-SHALookup
  name: FansDB-SHALookup
  version: ${VERSION}
  date: ${DATE}
  path: FansDB-SHALookup.zip
  sha256: ${SHA256}
  requires:
    - emojis
    - requests
    - lxml
    - stashapp-tools
EOF
