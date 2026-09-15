package com.nflsideline.coreapi;

import com.nflsideline.coreapi.snapshot.SnapshotBatchApplication;
import com.nflsideline.coreapi.editorial.batch.EditorialBatchApplication;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.util.Arrays;

@SpringBootApplication
public class CoreApiApplication {

    public static void main(String[] args) {
        if (args.length > 0 && "snapshot-export".equals(args[0])) {
            int exitCode = SnapshotBatchApplication.run(Arrays.copyOfRange(args, 1, args.length));
            if (exitCode != 0) {
                System.exit(exitCode);
            }
            return;
        }
        if (args.length > 0 && "editorial-generate".equals(args[0])) {
            int exitCode = EditorialBatchApplication.run(Arrays.copyOfRange(args, 1, args.length));
            if (exitCode != 0) System.exit(exitCode);
            return;
        }
        SpringApplication.run(CoreApiApplication.class, args);
    }

}
