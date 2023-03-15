# Skythonic
**Skythonic** is a wrapper for the cloud which aims to homogenize and simplify the cloud experience.

# Main goals
**Consistent, simple API**: Have "create" "assoc" "dissoc" and "delete" functions that have the same signature across platforms and resource types (with optional kv pairs)

**Presets at various levels of granularity**: Mid and high level functions are to be added which allows the user to control the level of detail they work at. 

# Development status
This project is very much **Pre-alpha** and is under active development. Only AWS has been worked on, but Azure is likely and, Google are others are a possibility.

# Skythonic vs Pulumi
This project has more overlap with other tools since it's more of a learning exercise.

**Pulumi** is *the* infrastructure-as-code platform if you only consider "code" to be general-purposes languages (not DSL's). Although the projects are similar, there are a couple of goals unique (I think!) to Skythonic: most notably the uniformity of the API.



