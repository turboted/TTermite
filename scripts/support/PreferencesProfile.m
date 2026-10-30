#import <Foundation/Foundation.h>
#import <CoreFoundation/CoreFoundation.h>
#import <objc/runtime.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Test infrastructure only. This library is built in an ignored directory and
// injected into test/smoke processes; it is never copied into a released App.
static NSURL *TTPreferencesContainer;
static void TTConfigurePreferences(NSUserDefaults *defaults) {
    SEL selector = NSSelectorFromString(@"_setContainer:");
    Method method = class_getInstanceMethod([NSUserDefaults class], selector);
    if (!method || !defaults) {
        fputs("Native preferences profile API unavailable; refusing unisolated tests.\n", stderr);
        abort();
    }
    typedef void (*Setter)(id, SEL, CFURLRef);
    ((Setter)method_getImplementation(method))(defaults, selector, (__bridge CFURLRef)TTPreferencesContainer);
}

static NSURL *TTDomainFile(NSString *name) {
    if (!name.length || [name containsString:@"/"] || [name isEqualToString:@"."] || [name isEqualToString:@".."]) abort();
    return [[TTPreferencesContainer URLByAppendingPathComponent:@"Library/Preferences" isDirectory:YES]
            URLByAppendingPathComponent:[name stringByAppendingString:@".plist"]];
}
static NSDictionary *TTReadDomain(NSString *name) {
    NSData *data = [NSData dataWithContentsOfURL:TTDomainFile(name)];
    if (!data) return nil;
    id object = [NSPropertyListSerialization propertyListWithData:data options:NSPropertyListImmutable format:nil error:nil];
    return [object isKindOfClass:[NSDictionary class]] ? object : nil;
}
static void TTReplaceDomain(NSString *name, NSDictionary *values) {
    NSUserDefaults *defaults = [name isEqualToString:[[NSBundle mainBundle] bundleIdentifier]]
        ? [NSUserDefaults standardUserDefaults] : [[NSUserDefaults alloc] initWithSuiteName:name];
    if (!defaults) { fputs("Unable to create explicit test preferences domain.\n", stderr); abort(); }
    if (![defaults synchronize]) abort();
    for (NSString *key in TTReadDomain(name)) [defaults removeObjectForKey:key];
    for (NSString *key in values) [defaults setObject:values[key] forKey:key];
    if (![defaults synchronize]) abort();
    if (!values) [[NSFileManager defaultManager] removeItemAtURL:TTDomainFile(name) error:nil];
}
@interface NSUserDefaults (TTReleaseProfile)
- (instancetype)tt_releaseProfileInitWithSuiteName:(NSString *)name __attribute__((objc_method_family(init)));
- (NSDictionary *)tt_releaseProfilePersistentDomainForName:(NSString *)name;
- (void)tt_releaseProfileSetPersistentDomain:(NSDictionary *)values forName:(NSString *)name;
- (void)tt_releaseProfileRemovePersistentDomainForName:(NSString *)name;
@end
@implementation NSUserDefaults (TTReleaseProfile)
- (instancetype)tt_releaseProfileInitWithSuiteName:(NSString *)name {
    self = [self tt_releaseProfileInitWithSuiteName:name];
    if (self) TTConfigurePreferences(self);
    return self;
}
- (NSDictionary *)tt_releaseProfilePersistentDomainForName:(NSString *)name {
    // AppKit also asks for OS-owned read-only domains (e.g. VoiceOver settings).
    // Read those from the empty test container without synchronizing the system
    // defaults object; no real accessibility preferences should enter a test.
    BOOL isSystemDomain = [name hasPrefix:@"com.apple."] || [name isEqualToString:NSGlobalDomain];
    if (!isSystemDomain && ![self synchronize]) {
        NSLog(@"Native test preferences could not synchronize domain %@", name);
        abort();
    }
    return TTReadDomain(name);
}
- (void)tt_releaseProfileSetPersistentDomain:(NSDictionary *)values forName:(NSString *)name { if (![self synchronize]) abort(); TTReplaceDomain(name, values); }
- (void)tt_releaseProfileRemovePersistentDomainForName:(NSString *)name { if (![self synchronize]) abort(); TTReplaceDomain(name, nil); }
@end

__attribute__((constructor)) static void TTInstallReleasePreferencesProfile(void) {
    const char *requested = getenv("TTERMITE_PROFILE_PREFERENCES");
    if (!requested || strcmp(requested, "1") != 0) return;
    @autoreleasepool {
        const char *home = getenv("TTERMITE_TEST_HOME");
        const char *fixedHome = getenv("CFFIXED_USER_HOME");
        if (!home || !fixedHome || home[0] != '/' || strlen(home) < 2 || strcmp(home, fixedHome) != 0) {
            fputs("A matching explicit native test HOME is required for preferences isolation.\n", stderr);
            abort();
        }
        TTPreferencesContainer = [NSURL fileURLWithPath:[NSString stringWithUTF8String:home] isDirectory:YES];
        NSError *error = nil;
        NSURL *preferences = [TTPreferencesContainer URLByAppendingPathComponent:@"Library/Preferences" isDirectory:YES];
        if (![[NSFileManager defaultManager] createDirectoryAtURL:preferences withIntermediateDirectories:YES attributes:nil error:&error]) abort();
        Method original = class_getInstanceMethod([NSUserDefaults class], @selector(initWithSuiteName:));
        Method replacement = class_getInstanceMethod([NSUserDefaults class], @selector(tt_releaseProfileInitWithSuiteName:));
        if (!original || !replacement) abort();
        method_exchangeImplementations(original, replacement);
        method_exchangeImplementations(class_getInstanceMethod([NSUserDefaults class], @selector(persistentDomainForName:)), class_getInstanceMethod([NSUserDefaults class], @selector(tt_releaseProfilePersistentDomainForName:)));
        method_exchangeImplementations(class_getInstanceMethod([NSUserDefaults class], @selector(setPersistentDomain:forName:)), class_getInstanceMethod([NSUserDefaults class], @selector(tt_releaseProfileSetPersistentDomain:forName:)));
        method_exchangeImplementations(class_getInstanceMethod([NSUserDefaults class], @selector(removePersistentDomainForName:)), class_getInstanceMethod([NSUserDefaults class], @selector(tt_releaseProfileRemovePersistentDomainForName:)));
        TTConfigurePreferences([NSUserDefaults standardUserDefaults]);
        NSURL *marker = [TTPreferencesContainer URLByAppendingPathComponent:@"PreferencesProfile.ready"];
        NSData *proof = [@"Native UserDefaults container configured before application entry.\n" dataUsingEncoding:NSUTF8StringEncoding];
        if (![proof writeToURL:marker options:NSDataWritingAtomic error:&error]) abort();
    }
}
