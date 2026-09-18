#!/usr/bin/env python3
"""Add MANICSKIN1 import/apply support to the proven native-only Manic baseline."""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MANICSKIN1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, got {count}")
    return text.replace(old, new, 1)


MANAGER_H = r'''// MANICSKIN1: installable native Manic skin packages (.manicskin).
#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

FOUNDATION_EXPORT NSString * const EKAManicBuiltinSkinID;

@interface EKAManicSkinManager : NSObject
+ (instancetype)sharedManager;
- (NSArray<NSDictionary<NSString *, NSString *> *> *)installedSkins;
- (NSString *)displayNameForSkinID:(nullable NSString *)skinID;
- (BOOL)importSkinAtURL:(NSURL *)url
        installedSkinID:(NSString * _Nullable * _Nullable)installedSkinID
                  error:(NSError * _Nullable * _Nullable)error;
- (void)setActiveSkinID:(nullable NSString *)skinID;
- (NSDictionary *)activeManifest;
- (nullable UIImage *)imageNamed:(NSString *)baseName;
@end

NS_ASSUME_NONNULL_END
'''

MANAGER_MM = r'''// MANICSKIN1: data-only .manicskin importer; no executable content.
#import "EKAManicSkinManager.h"

#include "miniz.h"

NSString * const EKAManicBuiltinSkinID = @"builtin";
static NSString * const EKAManicSkinErrorDomain = @"com.eka2l1.manicskin";
static const unsigned long long kEKAManicSkinMaxArchiveBytes = 30ull * 1024ull * 1024ull;
static const unsigned long long kEKAManicSkinMaxFileBytes = 10ull * 1024ull * 1024ull;
static const NSUInteger kEKAManicSkinMaxEntries = 128;

typedef NS_ENUM(NSInteger, EKAManicSkinErrorCode) {
    EKAManicSkinErrorInvalidFile = 1,
    EKAManicSkinErrorArchive,
    EKAManicSkinErrorUnsafePath,
    EKAManicSkinErrorUnsupportedContent,
    EKAManicSkinErrorManifest,
    EKAManicSkinErrorAsset,
    EKAManicSkinErrorInstall
};

static void EKAManicSetError(NSError **error, EKAManicSkinErrorCode code, NSString *message) {
    if (!error) return;
    *error = [NSError errorWithDomain:EKAManicSkinErrorDomain
                                 code:code
                             userInfo:@{NSLocalizedDescriptionKey: message ?: @"Invalid Manic skin"}];
}

static BOOL EKAManicSafeRelativePath(NSString *path) {
    if (path.length == 0 || [path hasPrefix:@"/"] || [path containsString:@"\\"]) return NO;
    for (NSString *part in path.pathComponents) {
        if ([part isEqualToString:@".."] || [part isEqualToString:@"."] || part.length == 0) return NO;
    }
    return YES;
}

static BOOL EKAManicAllowedArchivePath(NSString *path, BOOL directory) {
    if (directory) return YES;
    NSString *ext = path.pathExtension.lowercaseString;
    return [ext isEqualToString:@"json"] || [ext isEqualToString:@"png"];
}

static NSString *EKAManicNormalizedID(NSString *value) {
    if (![value isKindOfClass:NSString.class] || value.length == 0 || value.length > 64) return nil;
    NSCharacterSet *allowed = [NSCharacterSet characterSetWithCharactersInString:
        @"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"];
    return ([value rangeOfCharacterFromSet:allowed.invertedSet].location == NSNotFound) ? value : nil;
}

@interface EKAManicSkinManager ()
@property(nonatomic, copy) NSString *activeSkinID;
@property(nonatomic, strong) NSMutableDictionary<NSString *, UIImage *> *imageCache;
@end

@implementation EKAManicSkinManager

+ (instancetype)sharedManager {
    static EKAManicSkinManager *manager;
    static dispatch_once_t once;
    dispatch_once(&once, ^{ manager = [[EKAManicSkinManager alloc] init]; });
    return manager;
}

- (instancetype)init {
    if ((self = [super init])) {
        _activeSkinID = EKAManicBuiltinSkinID;
        _imageCache = [NSMutableDictionary dictionary];
    }
    return self;
}

- (NSURL *)skinsRootURL {
    NSURL *base = [[[NSFileManager defaultManager]
        URLsForDirectory:NSApplicationSupportDirectory
        inDomains:NSUserDomainMask] firstObject];
    NSURL *root = [base URLByAppendingPathComponent:@"ManicSkins" isDirectory:YES];
    [[NSFileManager defaultManager] createDirectoryAtURL:root
                              withIntermediateDirectories:YES
                                               attributes:nil
                                                    error:nil];
    return root;
}

- (NSURL *)skinDirectoryForID:(NSString *)skinID {
    return [[self skinsRootURL] URLByAppendingPathComponent:skinID isDirectory:YES];
}

- (NSDictionary *)builtInManifest {
    NSString *path = [[NSBundle mainBundle] pathForResource:@"info"
                                                    ofType:@"json"
                                               inDirectory:@"EKAManicControls"];
    NSData *data = path.length ? [NSData dataWithContentsOfFile:path] : nil;
    id obj = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
    return [obj isKindOfClass:NSDictionary.class] ? obj : @{};
}

- (NSDictionary *)manifestForSkinID:(NSString *)skinID {
    if (skinID.length == 0 || [skinID isEqualToString:EKAManicBuiltinSkinID]) return [self builtInManifest];
    NSURL *url = [[self skinDirectoryForID:skinID] URLByAppendingPathComponent:@"info.json"];
    NSData *data = [NSData dataWithContentsOfURL:url];
    id obj = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
    if (![obj isKindOfClass:NSDictionary.class]) return nil;
    if ([obj[@"format"] integerValue] != 1) return nil;
    if (![[obj[@"id"] description] isEqualToString:skinID]) return nil;
    return obj;
}

- (NSArray<NSDictionary<NSString *,NSString *> *> *)installedSkins {
    NSMutableArray *result = [NSMutableArray array];
    NSArray<NSURL *> *dirs = [[NSFileManager defaultManager]
        contentsOfDirectoryAtURL:[self skinsRootURL]
      includingPropertiesForKeys:nil
                         options:NSDirectoryEnumerationSkipsHiddenFiles
                           error:nil] ?: @[];
    for (NSURL *dir in dirs) {
        NSDictionary *m = [self manifestForSkinID:dir.lastPathComponent];
        if (!m) continue;
        NSString *sid = [m[@"id"] isKindOfClass:NSString.class] ? m[@"id"] : nil;
        NSString *name = [m[@"name"] isKindOfClass:NSString.class] ? m[@"name"] : nil;
        if (!sid.length || !name.length) continue;
        NSMutableDictionary *item = [@{@"id":sid, @"name":name} mutableCopy];
        if ([m[@"author"] isKindOfClass:NSString.class]) item[@"author"] = m[@"author"];
        if ([m[@"version"] isKindOfClass:NSString.class]) item[@"version"] = m[@"version"];
        [result addObject:item];
    }
    [result sortUsingComparator:^NSComparisonResult(NSDictionary *a, NSDictionary *b) {
        return [a[@"name"] localizedCaseInsensitiveCompare:b[@"name"]];
    }];
    return result;
}

- (NSString *)displayNameForSkinID:(NSString *)skinID {
    if (skinID.length == 0 || [skinID isEqualToString:EKAManicBuiltinSkinID]) return @"Built-in Manic";
    NSDictionary *m = [self manifestForSkinID:skinID];
    NSString *name = [m[@"name"] isKindOfClass:NSString.class] ? m[@"name"] : nil;
    return name.length ? name : @"Built-in Manic";
}

- (void)setActiveSkinID:(NSString *)skinID {
    NSString *candidate = skinID.length ? skinID : EKAManicBuiltinSkinID;
    if (![candidate isEqualToString:EKAManicBuiltinSkinID] && ![self manifestForSkinID:candidate]) {
        candidate = EKAManicBuiltinSkinID;
    }
    if (![_activeSkinID isEqualToString:candidate]) {
        _activeSkinID = [candidate copy];
        [_imageCache removeAllObjects];
    }
}

- (NSDictionary *)activeManifest {
    return [self manifestForSkinID:self.activeSkinID] ?: [self builtInManifest];
}

- (UIImage *)imageNamed:(NSString *)baseName {
    if (baseName.length == 0) return nil;
    NSString *clean = [baseName stringByDeletingPathExtension];
    NSString *cacheKey = [NSString stringWithFormat:@"%@:%@", self.activeSkinID, clean];
    UIImage *cached = self.imageCache[cacheKey];
    if (cached) return cached;

    NSString *path = nil;
    if ([self.activeSkinID isEqualToString:EKAManicBuiltinSkinID]) {
        path = [[NSBundle mainBundle] pathForResource:clean ofType:@"png" inDirectory:@"EKAManicControls"];
    } else {
        NSURL *root = [self skinDirectoryForID:self.activeSkinID];
        NSURL *asset = [root URLByAppendingPathComponent:[clean stringByAppendingPathExtension:@"png"]];
        path = asset.path;
    }
    UIImage *image = path.length ? [UIImage imageWithContentsOfFile:path] : nil;
    if (image) self.imageCache[cacheKey] = image;
    return image;
}

- (BOOL)validateManifestAtDirectory:(NSURL *)dir
                           manifest:(NSDictionary **)manifestOut
                              error:(NSError **)error {
    NSURL *manifestURL = [dir URLByAppendingPathComponent:@"info.json"];
    NSData *data = [NSData dataWithContentsOfURL:manifestURL];
    NSError *jsonError = nil;
    id obj = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:&jsonError] : nil;
    if (![obj isKindOfClass:NSDictionary.class]) {
        EKAManicSetError(error, EKAManicSkinErrorManifest, @"info.json is missing or invalid.");
        return NO;
    }

    NSDictionary *m = obj;
    if ([m[@"format"] integerValue] != 1) {
        EKAManicSetError(error, EKAManicSkinErrorManifest, @"Unsupported .manicskin format. Expected format 1.");
        return NO;
    }
    NSString *sid = EKAManicNormalizedID(m[@"id"]);
    NSString *name = [m[@"name"] isKindOfClass:NSString.class] ? m[@"name"] : nil;
    if (!sid.length || !name.length || name.length > 80) {
        EKAManicSetError(error, EKAManicSkinErrorManifest, @"Skin id/name is invalid.");
        return NO;
    }
    NSDictionary *reps = [m[@"representations"] isKindOfClass:NSDictionary.class] ? m[@"representations"] : nil;
    if (!reps.count) {
        EKAManicSetError(error, EKAManicSkinErrorManifest, @"Skin has no representations.");
        return NO;
    }

    NSMutableSet<NSString *> *assets = [NSMutableSet set];
    for (id devObj in reps.allValues) {
        if (![devObj isKindOfClass:NSDictionary.class]) continue;
        for (id styleObj in [(NSDictionary *)devObj allValues]) {
            if (![styleObj isKindOfClass:NSDictionary.class]) continue;
            for (id repObj in [(NSDictionary *)styleObj allValues]) {
                if (![repObj isKindOfClass:NSDictionary.class]) continue;
                NSArray *items = [repObj[@"items"] isKindOfClass:NSArray.class] ? repObj[@"items"] : @[];
                for (id itemObj in items) {
                    if (![itemObj isKindOfClass:NSDictionary.class]) continue;
                    NSDictionary *item = itemObj;
                    NSDictionary *asset = [item[@"asset"] isKindOfClass:NSDictionary.class] ? item[@"asset"] : nil;
                    NSString *normal = [asset[@"normal"] isKindOfClass:NSString.class] ? asset[@"normal"] : nil;
                    NSDictionary *thumb = [item[@"thumbstick"] isKindOfClass:NSDictionary.class] ? item[@"thumbstick"] : nil;
                    NSString *thumbName = [thumb[@"name"] isKindOfClass:NSString.class] ? thumb[@"name"] : nil;
                    if (normal.length) [assets addObject:normal];
                    if (thumbName.length) [assets addObject:thumbName];
                }
            }
        }
    }
    if (!assets.count) {
        EKAManicSetError(error, EKAManicSkinErrorManifest, @"Skin does not reference any control artwork.");
        return NO;
    }

    for (NSString *assetName in assets) {
        NSString *clean = [assetName stringByDeletingPathExtension];
        NSString *relative = [clean stringByAppendingPathExtension:@"png"];
        if (!EKAManicSafeRelativePath(relative)) {
            EKAManicSetError(error, EKAManicSkinErrorUnsafePath, @"Unsafe asset path in info.json.");
            return NO;
        }
        NSURL *assetURL = [dir URLByAppendingPathComponent:relative];
        UIImage *image = [UIImage imageWithContentsOfFile:assetURL.path];
        if (!image) {
            EKAManicSetError(error, EKAManicSkinErrorAsset,
                             [NSString stringWithFormat:@"Missing or invalid PNG: %@", relative]);
            return NO;
        }
        if (image.size.width > 4096 || image.size.height > 4096) {
            EKAManicSetError(error, EKAManicSkinErrorAsset,
                             [NSString stringWithFormat:@"PNG is too large: %@", relative]);
            return NO;
        }
    }

    if (manifestOut) *manifestOut = m;
    return YES;
}

- (BOOL)importSkinAtURL:(NSURL *)url
        installedSkinID:(NSString **)installedSkinID
                  error:(NSError **)error {
    if (![url.pathExtension.lowercaseString isEqualToString:@"manicskin"]) {
        EKAManicSetError(error, EKAManicSkinErrorInvalidFile, @"Choose a file ending in .manicskin.");
        return NO;
    }
    NSNumber *size = nil;
    [url getResourceValue:&size forKey:NSURLFileSizeKey error:nil];
    if (size.unsignedLongLongValue == 0 || size.unsignedLongLongValue > kEKAManicSkinMaxArchiveBytes) {
        EKAManicSetError(error, EKAManicSkinErrorInvalidFile, @"The .manicskin file is empty or larger than 30 MB.");
        return NO;
    }

    NSURL *root = [self skinsRootURL];
    NSURL *tmp = [root URLByAppendingPathComponent:
        [@".import-" stringByAppendingString:NSUUID.UUID.UUIDString] isDirectory:YES];
    NSFileManager *fm = NSFileManager.defaultManager;
    if (![fm createDirectoryAtURL:tmp withIntermediateDirectories:YES attributes:nil error:error]) return NO;

    mz_zip_archive zip;
    memset(&zip, 0, sizeof(zip));
    BOOL zipOpen = mz_zip_reader_init_file(&zip, url.fileSystemRepresentation, 0) != 0;
    if (!zipOpen) {
        [fm removeItemAtURL:tmp error:nil];
        EKAManicSetError(error, EKAManicSkinErrorArchive, @"The .manicskin file is not a readable ZIP archive.");
        return NO;
    }

    BOOL ok = YES;
    unsigned long long total = 0;
    mz_uint count = mz_zip_reader_get_num_files(&zip);
    if (count == 0 || count > kEKAManicSkinMaxEntries) {
        ok = NO;
        EKAManicSetError(error, EKAManicSkinErrorArchive, @"The skin has too many files.");
    }

    for (mz_uint i = 0; ok && i < count; ++i) {
        mz_zip_archive_file_stat stat;
        if (!mz_zip_reader_file_stat(&zip, i, &stat)) {
            ok = NO;
            EKAManicSetError(error, EKAManicSkinErrorArchive, @"Could not read a ZIP entry.");
            break;
        }
        NSString *relative = [NSString stringWithUTF8String:stat.m_filename ?: ""];
        BOOL directory = mz_zip_reader_is_file_a_directory(&zip, i) != 0;
        if (!EKAManicSafeRelativePath(relative)) {
            ok = NO;
            EKAManicSetError(error, EKAManicSkinErrorUnsafePath, @"Unsafe path found inside the skin.");
            break;
        }
        if (!EKAManicAllowedArchivePath(relative, directory)) {
            ok = NO;
            EKAManicSetError(error, EKAManicSkinErrorUnsupportedContent,
                             [NSString stringWithFormat:@"Unsupported file in skin: %@", relative]);
            break;
        }
        if (stat.m_uncomp_size > kEKAManicSkinMaxFileBytes ||
            total + stat.m_uncomp_size > kEKAManicSkinMaxArchiveBytes) {
            ok = NO;
            EKAManicSetError(error, EKAManicSkinErrorArchive, @"Uncompressed skin data exceeds the safety limit.");
            break;
        }
        total += stat.m_uncomp_size;

        NSURL *out = [tmp URLByAppendingPathComponent:relative isDirectory:directory];
        NSString *rootPrefix = [tmp.path stringByAppendingString:@"/"];
        if (![out.path hasPrefix:rootPrefix] && ![out.path isEqualToString:tmp.path]) {
            ok = NO;
            EKAManicSetError(error, EKAManicSkinErrorUnsafePath, @"Archive path escaped the skin directory.");
            break;
        }
        if (directory) {
            [fm createDirectoryAtURL:out withIntermediateDirectories:YES attributes:nil error:nil];
            continue;
        }
        [fm createDirectoryAtURL:[out URLByDeletingLastPathComponent]
      withIntermediateDirectories:YES attributes:nil error:nil];
        if (!mz_zip_reader_extract_to_file(&zip, i, out.fileSystemRepresentation, 0)) {
            ok = NO;
            EKAManicSetError(error, EKAManicSkinErrorArchive,
                             [NSString stringWithFormat:@"Could not extract %@", relative]);
            break;
        }
    }
    mz_zip_reader_end(&zip);

    NSDictionary *manifest = nil;
    if (ok) ok = [self validateManifestAtDirectory:tmp manifest:&manifest error:error];
    if (!ok) {
        [fm removeItemAtURL:tmp error:nil];
        return NO;
    }

    NSString *sid = EKAManicNormalizedID(manifest[@"id"]);
    if (!sid.length || [sid isEqualToString:EKAManicBuiltinSkinID]) {
        [fm removeItemAtURL:tmp error:nil];
        EKAManicSetError(error, EKAManicSkinErrorManifest, @"The skin id is reserved or invalid.");
        return NO;
    }

    NSURL *dst = [self skinDirectoryForID:sid];
    [fm removeItemAtURL:dst error:nil];
    NSError *moveError = nil;
    if (![fm moveItemAtURL:tmp toURL:dst error:&moveError]) {
        [fm removeItemAtURL:tmp error:nil];
        if (error) *error = moveError;
        return NO;
    }

    if (installedSkinID) *installedSkinID = sid;
    return YES;
}

@end
'''


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_manicskin1.py <upstream-root>")
    up = Path(sys.argv[1]).resolve()
    app = up / "src/emu/ios/app"
    manic_dir = app / "controls/manic"
    if not manic_dir.is_dir():
        fail("native Manic directory missing; restore NOJAVA FULL1 MANIC1 cache first")

    (manic_dir / "EKAManicSkinManager.h").write_text(MANAGER_H, encoding="utf-8")
    (manic_dir / "EKAManicSkinManager.mm").write_text(MANAGER_MM, encoding="utf-8")

    view_m = manic_dir / "EKAManicControlsView.m"
    text = view_m.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '#import "EKAManicControlsView.h"\n',
        '#import "EKAManicControlsView.h"\n#import "EKAManicSkinManager.h"\n',
        "Manic manager import",
    )
    old_resource = '''static NSString * const kEKAManicResourceDir = @"EKAManicControls";

static NSDictionary *EKAManicInfo(void) {
    static NSDictionary *info = nil;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        NSString *path = [[NSBundle mainBundle] pathForResource:@"info" ofType:@"json" inDirectory:kEKAManicResourceDir];
        NSData *data = path.length ? [NSData dataWithContentsOfFile:path] : nil;
        id obj = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
        if ([obj isKindOfClass:NSDictionary.class]) info = obj;
        if (!info) info = @{};
    });
    return info;
}

UIImage *EKAManicControlImage(NSString *baseName) {
    if (baseName.length == 0) return nil;
    NSString *clean = [baseName stringByDeletingPathExtension];
    NSString *path = [[NSBundle mainBundle] pathForResource:clean ofType:@"png" inDirectory:kEKAManicResourceDir];
    return path.length ? [UIImage imageWithContentsOfFile:path] : nil;
}
'''
    new_resource = '''static NSDictionary *EKAManicInfo(void) {
    return [[EKAManicSkinManager sharedManager] activeManifest];
}

UIImage *EKAManicControlImage(NSString *baseName) {
    return [[EKAManicSkinManager sharedManager] imageNamed:baseName];
}
'''
    text = replace_once(text, old_resource, new_resource, "dynamic Manic resources")
    view_m.write_text(text, encoding="utf-8")

    store_h = app / "GameSettingsStore.h"
    h = store_h.read_text(encoding="utf-8")
    h = replace_once(
        h,
        '@property (nonatomic, assign) NSInteger keyLayout;          // 0 = None, 1..4\n',
        '@property (nonatomic, assign) NSInteger keyLayout;          // 0=None, 1..7 (7=Manic)\n'
        '@property (nonatomic, copy) NSString *manicSkinID;          // builtin or installed .manicskin id\n',
        "settings header skin property",
    )
    store_h.write_text(h, encoding="utf-8")

    store_m = app / "GameSettingsStore.mm"
    m = store_m.read_text(encoding="utf-8")
    m = replace_once(m, '        _keyLayout = 0;\n',
                     '        _keyLayout = 0;\n        _manicSkinID = @"builtin";\n',
                     "settings default skin")
    m = replace_once(
        m,
        '        // 0=None, 1..4 built-in, 5 = "Layout 1.5 (#/*)", 6 = "Joystick".\n'
        '        s.keyLayout = MAX(0, MIN(6, [dict[@"keyLayout"] integerValue]));\n',
        '        // 0=None, 1..6 native built-ins, 7=Manic.\n'
        '        s.keyLayout = MAX(0, MIN(7, [dict[@"keyLayout"] integerValue]));\n',
        "layout 7 persistence clamp",
    )
    m = replace_once(
        m,
        '    if (dict[@"hapticFeedback"] != nil) {\n',
        '    if ([dict[@"manicSkinID"] isKindOfClass:NSString.class] && [dict[@"manicSkinID"] length]) {\n'
        '        s.manicSkinID = dict[@"manicSkinID"];\n'
        '    }\n'
        '    if (dict[@"hapticFeedback"] != nil) {\n',
        "skin settings load",
    )
    m = replace_once(
        m,
        '        @"keyLayout": @(settings.keyLayout),\n',
        '        @"keyLayout": @(settings.keyLayout),\n'
        '        @"manicSkinID": (settings.manicSkinID ?: @"builtin"),\n',
        "skin settings save",
    )
    store_m.write_text(m, encoding="utf-8")

    settings_vc = app / "GameSettingsViewController.mm"
    s = settings_vc.read_text(encoding="utf-8")
    s = replace_once(
        s,
        '#import "LayoutEditorViewController.h"\n',
        '#import "LayoutEditorViewController.h"\n'
        '#import "controls/manic/EKAManicSkinManager.h"\n'
        '#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>\n',
        "settings imports",
    )
    s = replace_once(
        s,
        '@interface GameSettingsViewController () <UITextFieldDelegate>\n',
        '@interface GameSettingsViewController () <UITextFieldDelegate, UIDocumentPickerDelegate>\n',
        "document picker delegate",
    )
    s = replace_once(
        s,
        '        case EKASectionKeyLayout: return 7;   // Layout + haptics + 3 editor entries + gyro + haptic passthrough\n',
        '        case EKASectionKeyLayout: return 8;   // Layout + Manic skin + haptics/editors/passthrough\n',
        "key layout row count",
    )
    s = replace_once(
        s,
        '        return EKAL(@"These settings apply only to this game.");\n',
        '        return _settings.keyLayout == 7\n'
        '            ? @".manicskin files change artwork/layout data only; Symbian/N-Gage scancodes remain native."\n'
        '            : EKAL(@"These settings apply only to this game.");\n',
        "Manic section footer",
    )

    old_cells = '''            } else if (indexPath.row == 1) {
                cell.textLabel.text = EKAL(@"Haptic Feedback");
                cell.detailTextLabel.text = nil;
                cell.selectionStyle = UITableViewCellSelectionStyleNone;
                UISwitch *sw = [[UISwitch alloc] init];
                sw.on = _settings.hapticFeedback;
                [sw addTarget:self action:@selector(onHapticChanged:) forControlEvents:UIControlEventValueChanged];
                cell.accessoryView = sw;
            } else if (indexPath.row == 2) {
                cell.textLabel.text = EKAL(@"Edit Layout (Portrait)");
                cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
            } else if (indexPath.row == 3) {
                cell.textLabel.text = EKAL(@"Edit Layout (Landscape)");
                cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
            } else if (indexPath.row == 4) {
                cell.textLabel.text = EKAL(@"Per-game Keybinds");
                cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
            } else if (indexPath.row == 5) {
                cell.textLabel.text = EKAL(@"Gyroscope Passthrough");
                cell.detailTextLabel.text = nil;
                cell.selectionStyle = UITableViewCellSelectionStyleNone;
                UISwitch *sw = [[UISwitch alloc] init];
                sw.on = _settings.gyroPassthrough;
                [sw addTarget:self action:@selector(onGyroChanged:) forControlEvents:UIControlEventValueChanged];
                cell.accessoryView = sw;
            } else {
                cell.textLabel.text = EKAL(@"Haptic Passthrough");
                cell.detailTextLabel.text = nil;
                cell.selectionStyle = UITableViewCellSelectionStyleNone;
                UISwitch *sw = [[UISwitch alloc] init];
                sw.on = _settings.hapticPassthrough;
                [sw addTarget:self action:@selector(onHapticPassthroughChanged:) forControlEvents:UIControlEventValueChanged];
                cell.accessoryView = sw;
            }
'''
    new_cells = '''            } else if (indexPath.row == 1) {
                cell.textLabel.text = @"Manic Skin";
                cell.detailTextLabel.text = [[EKAManicSkinManager sharedManager]
                    displayNameForSkinID:_settings.manicSkinID];
                cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
                cell.selectionStyle = UITableViewCellSelectionStyleDefault;
                cell.textLabel.enabled = (_settings.keyLayout == 7);
                cell.detailTextLabel.enabled = (_settings.keyLayout == 7);
            } else if (indexPath.row == 2) {
                cell.textLabel.text = EKAL(@"Haptic Feedback");
                cell.detailTextLabel.text = nil;
                cell.selectionStyle = UITableViewCellSelectionStyleNone;
                UISwitch *sw = [[UISwitch alloc] init];
                sw.on = _settings.hapticFeedback;
                [sw addTarget:self action:@selector(onHapticChanged:) forControlEvents:UIControlEventValueChanged];
                cell.accessoryView = sw;
            } else if (indexPath.row == 3) {
                cell.textLabel.text = EKAL(@"Edit Layout (Portrait)");
                cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
            } else if (indexPath.row == 4) {
                cell.textLabel.text = EKAL(@"Edit Layout (Landscape)");
                cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
            } else if (indexPath.row == 5) {
                cell.textLabel.text = EKAL(@"Per-game Keybinds");
                cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
            } else if (indexPath.row == 6) {
                cell.textLabel.text = EKAL(@"Gyroscope Passthrough");
                cell.detailTextLabel.text = nil;
                cell.selectionStyle = UITableViewCellSelectionStyleNone;
                UISwitch *sw = [[UISwitch alloc] init];
                sw.on = _settings.gyroPassthrough;
                [sw addTarget:self action:@selector(onGyroChanged:) forControlEvents:UIControlEventValueChanged];
                cell.accessoryView = sw;
            } else {
                cell.textLabel.text = EKAL(@"Haptic Passthrough");
                cell.detailTextLabel.text = nil;
                cell.selectionStyle = UITableViewCellSelectionStyleNone;
                UISwitch *sw = [[UISwitch alloc] init];
                sw.on = _settings.hapticPassthrough;
                [sw addTarget:self action:@selector(onHapticPassthroughChanged:) forControlEvents:UIControlEventValueChanged];
                cell.accessoryView = sw;
            }
'''
    s = replace_once(s, old_cells, new_cells, "Manic skin settings cell")

    methods_anchor = '''- (void)openLayoutEditorPortrait:(BOOL)portrait {
'''
    methods = r'''- (void)applyManicSkinID:(NSString *)skinID {
    _settings.manicSkinID = skinID.length ? skinID : EKAManicBuiltinSkinID;
    _settings.keyLayout = 7;
    [self persistAndNotify];
    [self.tableView reloadSections:[NSIndexSet indexSetWithIndex:EKASectionKeyLayout]
                  withRowAnimation:UITableViewRowAnimationNone];
}

- (void)openManicSkinImporter {
    UIDocumentPickerViewController *picker =
        [[UIDocumentPickerViewController alloc] initForOpeningContentTypes:@[UTTypeData] asCopy:YES];
    picker.delegate = self;
    picker.allowsMultipleSelection = NO;
    [self presentViewController:picker animated:YES completion:nil];
}

- (void)pickManicSkinFromCell:(UITableViewCell *)cell {
    if (_settings.keyLayout != 7) return;
    EKAManicSkinManager *manager = [EKAManicSkinManager sharedManager];
    UIAlertController *sheet = [UIAlertController alertControllerWithTitle:@"Manic Skin"
        message:@"Choose an installed skin or import a .manicskin file."
        preferredStyle:UIAlertControllerStyleActionSheet];

    NSString *current = _settings.manicSkinID.length ? _settings.manicSkinID : EKAManicBuiltinSkinID;
    NSString *builtinTitle = [current isEqualToString:EKAManicBuiltinSkinID]
        ? @"Built-in Manic  ✓" : @"Built-in Manic";
    [sheet addAction:[UIAlertAction actionWithTitle:builtinTitle style:UIAlertActionStyleDefault
        handler:^(UIAlertAction *a) { [self applyManicSkinID:EKAManicBuiltinSkinID]; }]];

    for (NSDictionary<NSString *, NSString *> *skin in manager.installedSkins) {
        NSString *sid = skin[@"id"], *name = skin[@"name"];
        NSString *title = [sid isEqualToString:current] ? [name stringByAppendingString:@"  ✓"] : name;
        [sheet addAction:[UIAlertAction actionWithTitle:title style:UIAlertActionStyleDefault
            handler:^(UIAlertAction *a) { [self applyManicSkinID:sid]; }]];
    }

    [sheet addAction:[UIAlertAction actionWithTitle:@"Import .manicskin…"
        style:UIAlertActionStyleDefault
        handler:^(UIAlertAction *a) { [self openManicSkinImporter]; }]];
    [sheet addAction:[UIAlertAction actionWithTitle:EKAL(@"Cancel") style:UIAlertActionStyleCancel handler:nil]];
    sheet.popoverPresentationController.sourceView = cell;
    sheet.popoverPresentationController.sourceRect = cell.bounds;
    [self presentViewController:sheet animated:YES completion:nil];
}

- (void)documentPicker:(UIDocumentPickerViewController *)controller
    didPickDocumentsAtURLs:(NSArray<NSURL *> *)urls {
    (void)controller;
    NSURL *url = urls.firstObject;
    if (!url) return;

    BOOL scoped = [url startAccessingSecurityScopedResource];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        NSError *error = nil;
        NSString *skinID = nil;
        BOOL ok = [[EKAManicSkinManager sharedManager] importSkinAtURL:url
                                                       installedSkinID:&skinID
                                                                 error:&error];
        if (scoped) [url stopAccessingSecurityScopedResource];
        dispatch_async(dispatch_get_main_queue(), ^{
            if (!ok) {
                UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Invalid Manic Skin"
                    message:error.localizedDescription ?: @"The .manicskin file could not be imported."
                    preferredStyle:UIAlertControllerStyleAlert];
                [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
                [self presentViewController:alert animated:YES completion:nil];
                return;
            }
            [self applyManicSkinID:skinID];
            NSString *name = [[EKAManicSkinManager sharedManager] displayNameForSkinID:skinID];
            UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Manic Skin Installed"
                message:[NSString stringWithFormat:@"%@ is now active for this game.", name]
                preferredStyle:UIAlertControllerStyleAlert];
            [alert addAction:[UIAlertAction actionWithTitle:@"OK" style:UIAlertActionStyleDefault handler:nil]];
            [self presentViewController:alert animated:YES completion:nil];
        });
    });
}

'''
    s = replace_once(s, methods_anchor, methods + methods_anchor, "Manic skin UI methods")

    old_select = '''        if (indexPath.row == 0)      [self pickLayoutFromCell:cell];
        else if (indexPath.row == 1) { /* Haptic Feedback — the switch handles it */ }
        else if (indexPath.row == 2) [self openLayoutEditorPortrait:YES];
        else if (indexPath.row == 3) [self openLayoutEditorPortrait:NO];
        else if (indexPath.row == 4) [self openPerGameKeybinds];
        else if (indexPath.row == 5) { /* Gyroscope Passthrough — the switch handles it */ }
        else                         { /* Haptic Passthrough — the switch handles it */ }
'''
    new_select = '''        if (indexPath.row == 0)      [self pickLayoutFromCell:cell];
        else if (indexPath.row == 1) [self pickManicSkinFromCell:cell];
        else if (indexPath.row == 2) { /* Haptic Feedback — the switch handles it */ }
        else if (indexPath.row == 3) [self openLayoutEditorPortrait:YES];
        else if (indexPath.row == 4) [self openLayoutEditorPortrait:NO];
        else if (indexPath.row == 5) [self openPerGameKeybinds];
        else if (indexPath.row == 6) { /* Gyroscope Passthrough — the switch handles it */ }
        else                         { /* Haptic Passthrough — the switch handles it */ }
'''
    s = replace_once(s, old_select, new_select, "Manic skin row interaction")
    settings_vc.write_text(s, encoding="utf-8")

    root = app / "RootViewController.mm"
    r = root.read_text(encoding="utf-8")
    r = replace_once(
        r,
        '#import "controls/manic/EKAManicControlsView.h"\n',
        '#import "controls/manic/EKAManicControlsView.h"\n'
        '#import "controls/manic/EKAManicSkinManager.h"\n',
        "root manager import",
    )
    r = replace_once(
        r,
        '    BOOL useManic = (self.keyLayout == 7);\n'
        '    NSArray<NSDictionary *> *activeLayout = custom.count ? custom : nil;\n',
        '    BOOL useManic = (self.keyLayout == 7);\n'
        '    [[EKAManicSkinManager sharedManager] setActiveSkinID:(useManic ? s.manicSkinID : EKAManicBuiltinSkinID)];\n'
        '    NSArray<NSDictionary *> *activeLayout = custom.count ? custom : nil;\n',
        "activate selected Manic skin",
    )
    root.write_text(r, encoding="utf-8")

    cmake = up / "src/emu/ios/CMakeLists.txt"
    c = cmake.read_text(encoding="utf-8")
    c = replace_once(
        c,
        'target_sources(eka2l1 PRIVATE\n'
        '    app/controls/manic/EKAManicControlsView.h\n'
        '    app/controls/manic/EKAManicControlsView.m)\n',
        'target_sources(eka2l1 PRIVATE\n'
        '    app/controls/manic/EKAManicControlsView.h\n'
        '    app/controls/manic/EKAManicControlsView.m\n'
        '    app/controls/manic/EKAManicSkinManager.h\n'
        '    app/controls/manic/EKAManicSkinManager.mm)\n'
        'target_include_directories(eka2l1 PRIVATE "${PROJECT_SOURCE_DIR}/src/external/miniz")\n',
        "CMake manager source",
    )
    cmake.write_text(c, encoding="utf-8")

    checks = {
        manic_dir / "EKAManicSkinManager.mm": [".manicskin", "mz_zip_reader_init_file", "format"],
        settings_vc: ["UIDocumentPickerDelegate", "Import .manicskin", "Manic Skin"],
        store_h: ["manicSkinID"],
        store_m: ['MIN(7, [dict[@"keyLayout"] integerValue])', '"manicSkinID"'],
        root: ["setActiveSkinID", "manicSkinID"],
        cmake: ["EKAManicSkinManager.mm", "src/external/miniz"],
    }
    for p, needles in checks.items():
        data = p.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in data:
                fail(f"gate missing {needle!r} in {p}")

    print("MANICSKIN1 import/select/persistence source gates: PASS")


if __name__ == "__main__":
    main()
