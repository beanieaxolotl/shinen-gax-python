# Replayer compatibility

### Playback features
|Feature                         |Accuracy                                                                           |
|--------------------------------|-----------------------------------------------------------------------------------|
|Note off                        |95% - Note offs are affected by speed modulation when they shouldn't be            |
|Wave parameters                 |0% - Iridion II relies on the wave parameters being accurate                       |
|Vibrato                         |66% - Vibrato depth is inaccurate (it is either too deep or shallow)               |
|Perf list handling              |50% - One-row perf lists are handled improperly (cases - the Madagascar GBA games) |


### Volume envelope handling
|Feature                         |Accuracy                                                    |
|--------------------------------|------------------------------------------------------------|
|Basic volume envelope handling  |100%                                                        |
|Envelope looping                |50% - Slightly too fast, can sometimes break                |
|Envelope sustain                |100%                                                        |
|Envelope sustain + looping      |0% - Envelopes with both sustain and loop can't be stopped  |


### Perf. effects/commands

|Value    |Name                            |Accuracy                                 |
|---------|--------------------------------|-----------------------------------------|
|0x00     |No effect                       |N/A                                      |
|0x01     |Portamento up                   |100%                                     |
|0x02     |Portamento down                 |100%                                     |
|0x05     |Jump to given perf. row         |100%                                     |
|0x06     |Delay row jump                  |untested                                 |
|0x0A     |Volume slide up                 |untested                                 |
|0x0B     |Volume slide down               |untested                                 |
|0x0C     |Set volume                      |100%                                     |
|0x0F     |Set speed                       |100%                                     |

### Effects/commands

|Value    |Name                            |Accuracy                                            |
|---------|--------------------------------|----------------------------------------------------|
|0x00     |No effect                       |N/A                                                 |
|0x01     |Portamento up                   |100%                                                |
|0x02     |Portamento down                 |100%                                                |
|0x03     |Tone portamento                 |75% - One note slides are too fast                  |
|0x07     |Speed modulation                |100%                                                |
|0x0A     |Volume slide up                 |100%                                                |
|0x0B     |Volume slide down               |100%                                                |
|0x0C     |Set volume                      |100%                                                |
|0x0D     |Break pattern                   |100% - Param is ignored like the actual GAX         |
|0xED     |Delay note                      |0% - This is ignored for right now                  |
|0x0F     |Set speed                       |100%                                                |
